from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_role, get_current_user
from app.models import LoanProduct, User, LoanApplication, Installment, Loan
from app.schemas import LoanApplicationOutput, LoanApplicationCreate, ApplicationDecision
from app.services.eligibility import assess_application
from app.services.repayment_schedule import generate_schedule
from app.services.audit import log_action
from decimal import Decimal


router = APIRouter(prefix='/loan-applications', tags=['Loan Applications'])

@router.post("", response_model=LoanApplicationOutput, status_code=status.HTTP_201_CREATED)
def create_application(application: LoanApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    ):
    if current_user.role != 'BORROWER':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only borrowers can submit loan application'
    )
    product = db.query(LoanProduct).filter(LoanProduct.id==application.loan_product_id).first()
    if product is None or not product.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Loan product not found or inactive'
        )
    if not (product.min_amount <= application.requested_amount <= product.max_amount):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Requested amount must be between {product.min_amount} and {product.max_amount}"
        )
    if application.requested_term_months > product.max_term_months:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Requested term must not exceed {product.max_term_months} months"
        )
    existing_application = db.query(LoanApplication).filter(
        LoanApplication.borrower_id == current_user.id, 
        LoanApplication.status == 'PENDING').first()
    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='You already have a pending loan application'
        )
    new_application = LoanApplication(
        borrower_id = current_user.id,
        loan_product_id = application.loan_product_id,
        requested_amount = application.requested_amount,
        requested_term_months = application.requested_term_months,
        monthly_income = application.monthly_income,
        status = 'PENDING'
    )
    db.add(new_application)
    db.commit()
    db.refresh(new_application)

    return new_application

@router.get('/{application_id}', response_model=LoanApplicationOutput)
def get_application(application_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    application = db.query(LoanApplication).filter(LoanApplication.id == application_id).first()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Application not found'
        )
    if current_user.role == 'BORROWER' and application.borrower_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Not accessible'
        )
    if current_user.role not in {
        'BORROWER', 'LENDING_OFFICER', 'SYSTEM_ADMIN'
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Not accessible'
        )
    return application


@router.post('/{application_id}/decision')
def decide_application(
    application_id: int, 
    decision: ApplicationDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only lending officers and system admin can decide
    role = current_user.role.strip().upper().replace(" ", "_")
    if role not in {"LENDING_OFFICER", "SYSTEM_ADMIN"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to do this"
        )

    # Find the application
    application = db.query(LoanApplication).filter(LoanApplication.id == application_id).first()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Application not found'
        )

    # Only pending application can receive decision
    if application.status != 'PENDING':
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Apllication already decided'
        )

        
    # Handle rejection
    if decision.decision == 'REJECT':
        if not decision.rejection_reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail='Rejection reason required'
            )

        application.status = 'REJECTED'
        application.rejection_reason = decision.rejection_reason

        log_action(
            db,
            actor_user_id=current_user.id,
            action='APPLICATION REJECTED',
            resource_type='LOAN_APPLICATION',
            resource_id=application.id,
            details={
                'new_status': 'REJECTED',
                'reason': application.rejection_reason
            }
        )

        db.commit()
        db.refresh(application)

        return {
            "message": "Application rejected",
            "application_id": application.id,
            "status": application.status,
            "rejection_reason": application.rejection_reason
        }

    # Load product
    product = db.query(LoanProduct).filter(LoanProduct.id == application.loan_product_id).first()
    if product is None or not product.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Loan product not found or inactive'
        )
    result = assess_application(application, product)
    if not result.eligible:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Application not eligible: {result.reason}"
        )

    # Approve, create loan and repayment schedule
    try:
        application.status = 'APPROVED'
        loan = Loan(
            application_id=application.id,
            borrower_id=application.borrower_id,
            loan_product_id=application.loan_product_id,
            principal_amount=application.requested_amount,
            interest_rate=product.interest_rate,
            term_months=application.requested_term_months,
            outstanding_balance=application.requested_amount,
            status='ACTIVE'
        )
        db.add(loan)
        db.flush()
        installments = generate_schedule(loan)
        db.add_all(installments)

        log_action(
            db,
            actor_user_id=current_user.id,
            action='APPLICATION APPROVED',
            resource_type='LOAN_APPLICATION',
            resource_id=application.id,
            details={
                'new_status':'APPROVED',
                'loan_id':loan.id,
            }
        )

        log_action(
                    db,
                    actor_user_id=current_user.id,
                    action='LOAN CREATED',
                    resource_type='LOAN',
                    resource_id=application.id,
                    details={
                        'application_id': application.id,
                        'borrower_id': application.borrower_id
                    }
                )

        loan.outstanding_balance = sum((i.amount_due for i in installments), Decimal('0.00'))
        db.commit()
        db.refresh(loan)

    except Exception:
        db.rollback()
        raise

    return {
        "msg": "Application approved and loan created",
        "application_id": application.id,
        "application_status": application.status,
        "loan_id": loan.id,
        "loan_status": loan.status,
        "installments": len(installments)
    }

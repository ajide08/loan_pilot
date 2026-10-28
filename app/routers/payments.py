from fastapi import APIRouter, Depends, HTTPException, status, Response, Header
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Repayment, Loan, Installment
from app.schemas import RepaymentCreate, RepaymentOutput
from app.services.audit import log_action

from decimal import Decimal
from uuid import uuid4
from datetime import date

router = APIRouter(prefix='/loans', tags=['Loan Payments'])

@router.post('/{loan_id}/payments', response_model=RepaymentOutput, status_code=status.HTTP_201_CREATED)
def record_payment(
    loan_id: int,
    repayment: RepaymentCreate,
    response: Response = None,
    idempotency_key: str = Header(
            ...,
            alias='Idempotency-Key',
            min_length=2,
            max_length=100
        ),    
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    
):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()

    if loan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Loan not found'
        )
    
    if loan.borrower_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You are not authorized to make payments for this loan'
        )
    existing_payment = (
        db.query(Repayment)
        .filter(Repayment.idempotency_key == idempotency_key)
        .first()
        )
    
    if existing_payment is not None:
        if (
            existing_payment.loan_id != loan.id
            or existing_payment.amount != repayment.amount
        ):
            raise HTTPException(
                status_code=409,
                detail="Idempotency key was already used for a different request",
            )
    
        response.status_code = status.HTTP_200_OK
    
        return {
            "id": existing_payment.id,
            "loan_id": existing_payment.loan_id,
            "amount": existing_payment.amount,
            "status": existing_payment.status,
            "reference": existing_payment.reference,
            "remaining_balance": loan.outstanding_balance,
        }

    if loan.status == 'PAID' or loan.outstanding_balance <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='This loan has already been fully repaid'
        )

    if loan.status not in ['ACTIVE', 'OVERDUE']:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='This loan is not in a state that allows repayments'
        )

    amount = repayment.amount

    if amount > loan.outstanding_balance:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f'Payment amount exceeds outstanding balance of {loan.outstanding_balance}'
        )

    installments = (
        db.query(Installment)
        .filter(Installment.loan_id == loan.id)
        .filter(Installment.status.in_(["PENDING", "PARTIAL", "OVERDUE"]))
        .order_by(Installment.installment_number.asc())
        .all()
    )

    if not installments:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='No pending installments found for this loan'
        )

    schedule_remaining = sum((i.amount_due - i.amount_paid for i in installments), Decimal('0.00'))
    if schedule_remaining != loan.outstanding_balance:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Outstanding balance does not match the sum of remaining installments'
        )


    repayment = Repayment(
        loan_id=loan.id,
        amount=amount,
        status='SUCCESS',
        reference=f'LP-{uuid4().hex}',
        idempotency_key=idempotency_key,
    )

    try:
        db.add(repayment)
        db.flush()

        remaining_payment = amount
        for i in installments:
            if remaining_payment <= 0:
                break

            installment_remaining = (i.amount_due - i.amount_paid)
            amount_to_apply = min(remaining_payment, installment_remaining)

            i.amount_paid += amount_to_apply
            remaining_payment -= amount_to_apply

            if i.amount_paid == i.amount_due:
                i.status = 'PAID'
            elif i.due_date.date() < date.today():
                i.status = 'OVERDUE'
            else:
                i.status = 'PARTIAL'

        if remaining_payment != 0:
            raise ValueError(
                "Payment could not be fully allocated to installments"
            )

        loan.outstanding_balance -= amount

        if loan.outstanding_balance == Decimal("0.00"):
            loan.status = "PAID"
        else:
            has_overdue_installment = any(i.status == 'OVERDUE' for i in installments)
            loan.status = 'OVERDUE' if has_overdue_installment else 'ACTIVE'

        log_action(
            db,
            actor_user_id=current_user.id,
            action='PAYMENT_RECORDED',
            resource_type='REPAYMENT',
            resource_id=repayment.id,
            details={
                'loan_id': loan.id,
                'amount':str(repayment.amount),
                'status': repayment.status
            }
        )

        db.commit()
        db.refresh(repayment)


    except Exception as e:
        db.rollback()
        raise
    return {
        "id": repayment.id,
        "loan_id": repayment.loan_id,
        "amount": repayment.amount,
        "status": repayment.status,
        "reference": repayment.reference,
        "remaining_balance": loan.outstanding_balance,
    }
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_role
from app.models import LoanProduct, User
from app.schemas import LoanProductCreate, LoanProductOutput, LoanProductUpdate

router = APIRouter(prefix='/loan-products', tags=['Loan Products'])

@router.post('', response_model=LoanProductOutput, status_code=status.HTTP_201_CREATED)
def create_loan_product(product: LoanProductCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_role('SYSTEM_ADMIN'))):

    existing_product = db.query(LoanProduct).filter(LoanProduct.name == product.name).first()
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Loan product with this name already exists",
        )
    new_product = LoanProduct(
        name=product.name, 
        interest_rate=product.interest_rate,
        min_amount=product.min_amount,
        max_amount=product.max_amount,
        max_term_months=product.max_term_months,
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    return new_product

@router.get("", response_model=list[LoanProductOutput])
def get_loan_products(db: Session = Depends(get_db)):
    return db.query(LoanProduct).all()

@router.patch("/{product_id}", response_model=LoanProductOutput)
def update_loan_product( 
    product_id: int,
    product: LoanProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role('SYSTEM_ADMIN'))):

    loan_product = db.query(LoanProduct).filter(LoanProduct.id == product_id).first()
    if loan_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Loan product not found",
        )
    
    proposed_min = (
        product.min_amount
        if product.min_amount is not None
        else loan_product.min_amount
    )
    proposed_max = (
        product.max_amount
        if product.max_amount is not None
        else loan_product.max_amount
    )

    if proposed_min > proposed_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Minimum amount cannot exceed maximum amount",
        )


    if product.name is not None:
        loan_product.name = product.name
    if product.interest_rate is not None:
        loan_product.interest_rate = product.interest_rate
    if product.min_amount is not None:
        loan_product.min_amount = product.min_amount
    if product.max_amount is not None:
        loan_product.max_amount = product.max_amount
    if product.max_term_months is not None:
        loan_product.max_term_months = product.max_term_months
    if product.active is not None:
        loan_product.active = product.active

    db.commit()
    db.refresh(loan_product)

    return loan_product
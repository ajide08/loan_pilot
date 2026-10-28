from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from decimal import Decimal
from datetime import datetime 

class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    role: str | None = None
    user: UserResponse | None = None



class LoanProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    interest_rate: Decimal = Field(ge=0, max_digits=5, decimal_places=2)
    min_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    max_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    max_term_months: int = Field(gt=0, le=120)

    @model_validator(mode="after")
    def validate_amount_range(self):
        if self.min_amount > self.max_amount:
            raise ValueError("Minimum amount cannot exceed maximum amount")
        return self


class LoanProductOutput(BaseModel):
    id: int
    name: str
    interest_rate: Decimal
    min_amount: Decimal
    max_amount: Decimal
    max_term_months: int

    class Config:
        from_attributes = True

class LoanProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    interest_rate: Decimal | None = Field(gt=0, default=None, max_digits=5, decimal_places=2)
    min_amount: Decimal | None = Field(gt=0, default=None, max_digits=12, decimal_places=2)
    max_amount: Decimal | None = Field(gt=0, default=None, max_digits=12, decimal_places=2)
    max_term_months: int | None = Field(gt=0, le=120, default=None)
    active: bool | None = None

    @model_validator(mode="after")
    def validate_amount_range(self):
        if (
            self.min_amount is not None
            and self.max_amount is not None
            and self.min_amount > self.max_amount
        ):
            raise ValueError("Minimum amount cannot exceed maximum amount")
        return self


class LoanApplicationCreate(BaseModel):
    loan_product_id: int = Field(gt=0)
    requested_amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    requested_term_months: int = Field(gt=0, le=120)
    monthly_income: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class LoanApplicationOutput(BaseModel):
    id: int
    borrower_id: int
    loan_product_id: int
    requested_amount: Decimal
    requested_term_months: int
    monthly_income: Decimal
    status: str
    rejection_reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationDecision(BaseModel):
    decision: Literal['APPROVE', 'REJECT']
    rejection_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_rejection_reason(self):
        if self.decision == 'REJECT':
            if not self.rejection_reason or not self.rejection_reason.strip():
                raise ValueError(
                    "A rejection reason is required when rejecting an application"
                )
        return self

class RepaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

class RepaymentOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_id: int
    amount: Decimal
    status: str
    reference: str
    remaining_balance: Decimal
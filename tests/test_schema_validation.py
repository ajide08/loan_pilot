import pytest
from pydantic import ValidationError
from app.schemas import (
    LoanApplicationCreate,
    LoanProductCreate,
    RepaymentCreate,
    ApplicationDecision
)


def test_loan_product_rejects_invalid_amount_range():
    with pytest.raises(ValidationError):
        LoanProductCreate(
            name="Personal Loan",
            interest_rate = 5.0,
            min_amount=10000,
            max_amount=5000,
            max_term_months=12
        )

def test_loan_application_rejects_negative_amount():
    with pytest.raises(ValidationError):
        LoanApplicationCreate(
            loan_product_id=1,
            requested_amount=-5000,
            requested_term_months=12,
            monthly_income=100000
        )

def test_repayment_rejects_zero_amount():
    with pytest.raises(ValidationError):
        RepaymentCreate(amount=0)

def test_rejection_requires_reason():
    with pytest.raises(ValidationError):
        ApplicationDecision(decision="REJECT")

def test_approval_does_not_require_reason():
    decision = ApplicationDecision(decision="APPROVE")
    assert decision.decision == "APPROVE"

def test_application_decision_parses_approval():
    decision = ApplicationDecision.model_validate(
        {"decision": "APPROVE"}
    )

    assert decision.decision == "APPROVE"
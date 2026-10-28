
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models import (
    AuditLog,
    Installment,
    Loan,
    LoanApplication,
    LoanProduct,
    User,
)
from app.services.overdue import process_overdue_installments


def setup_loan(db_session, loan_status="ACTIVE", balance="1000.00"):
    borrower = User(
        full_name="Overdue Service Borrower",
        email="overdue.service@example.com",
        password_hash="test-hash",
        role="BORROWER",
    )
    product = LoanProduct(
        name="Overdue Service Product",
        interest_rate=Decimal("10.00"),
        min_amount=Decimal("100.00"),
        max_amount=Decimal("10000.00"),
        max_term_months=24,
        active=True,
    )

    db_session.add_all([borrower, product])
    db_session.flush()

    application = LoanApplication(
        borrower_id=borrower.id,
        loan_product_id=product.id,
        requested_amount=Decimal("1000.00"),
        requested_term_months=12,
        monthly_income=Decimal("2000.00"),
        status="APPROVED",
    )
    db_session.add(application)
    db_session.flush()

    loan = Loan(
        application_id=application.id,
        borrower_id=borrower.id,
        loan_product_id=product.id,
        principal_amount=Decimal("1000.00"),
        interest_rate=Decimal("10.00"),
        term_months=12,
        outstanding_balance=Decimal(balance),
        status=loan_status,
    )
    db_session.add(loan)
    db_session.flush()
    return loan


def add_installment(
    db_session,
    loan,
    due_date,
    status="PENDING",
    amount_due="100.00",
    amount_paid="0.00",
):
    installment = Installment(
        loan_id=loan.id,
        installment_number=1,
        due_date=due_date,
        amount_due=Decimal(amount_due),
        amount_paid=Decimal(amount_paid),
        status=status,
    )
    db_session.add(installment)
    db_session.flush()
    return installment


def test_marks_past_due_installment_and_loan_overdue(db_session):
    today = date(2026, 10, 26)
    loan = setup_loan(db_session)
    installment = add_installment(
        db_session,
        loan,
        datetime.combine(today - timedelta(days=1), datetime.min.time()),
    )

    result = process_overdue_installments(db_session, today=today)

    db_session.refresh(loan)
    db_session.refresh(installment)

    assert result == {
        "installments_marked_overdue": 1,
        "loans_marked_overdue": 1,
        "loans_reactivated": 0,
    }
    assert installment.status == "OVERDUE"
    assert loan.status == "OVERDUE"


def test_does_not_mark_installment_due_today_overdue(db_session):
    today = date(2026, 10, 26)
    loan = setup_loan(db_session)
    installment = add_installment(
        db_session,
        loan,
        datetime.combine(today, datetime.min.time()),
    )

    result = process_overdue_installments(db_session, today=today)

    db_session.refresh(installment)
    db_session.refresh(loan)

    assert result["installments_marked_overdue"] == 0
    assert installment.status == "PENDING"
    assert loan.status == "ACTIVE"


def test_reactivates_loan_when_no_overdue_installments_remain(db_session):
    today = date(2026, 10, 26)
    loan = setup_loan(db_session, loan_status="OVERDUE")
    installment = add_installment(
        db_session,
        loan,
        datetime.combine(today, datetime.min.time()),
        status="PAID",
    )

    result = process_overdue_installments(db_session, today=today)

    db_session.refresh(loan)
    db_session.refresh(installment)

    assert result["loans_reactivated"] == 1
    assert loan.status == "ACTIVE"
    assert installment.status == "PAID"


def test_marks_loan_paid_when_balance_is_zero(db_session):
    today = date(2026, 10, 26)
    loan = setup_loan(db_session, balance="0.00")
    installment = add_installment(
        db_session,
        loan,
        datetime.combine(today - timedelta(days=3), datetime.min.time()),
    )

    result = process_overdue_installments(db_session, today=today)

    db_session.refresh(loan)
    db_session.refresh(installment)

    assert loan.status == "PAID"
    assert installment.status == "PENDING"
    assert result["installments_marked_overdue"] == 0


def test_repeat_processing_does_not_double_count_overdue_items(db_session):
    today = date(2026, 10, 26)
    loan = setup_loan(db_session)
    add_installment(
        db_session,
        loan,
        datetime.combine(today - timedelta(days=1), datetime.min.time()),
    )

    first = process_overdue_installments(db_session, today=today)
    second = process_overdue_installments(db_session, today=today)

    assert first["installments_marked_overdue"] == 1
    assert second["installments_marked_overdue"] == 0
    assert second["loans_marked_overdue"] == 0

    assert db_session.query(AuditLog).filter_by(
        action="OVERDUE_PROCESSING_COMPLETED"
    ).count() == 2


def test_partial_installment_can_become_overdue(db_session):
    today = date(2026, 10, 26)
    loan = setup_loan(db_session)
    installment = add_installment(
        db_session,
        loan,
        datetime.combine(today - timedelta(days=2), datetime.min.time()),
        status="PARTIAL",
        amount_due="100.00",
        amount_paid="25.00",
    )

    result = process_overdue_installments(db_session, today=today)

    db_session.refresh(installment)

    assert installment.status == "OVERDUE"
    assert result["installments_marked_overdue"] == 1

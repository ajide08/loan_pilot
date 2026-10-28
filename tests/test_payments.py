from datetime import datetime
from decimal import Decimal

from app.dependencies import get_current_user
from app.main import app
from app.models import Installment, Loan, LoanApplication, LoanProduct, User, Repayment



def test_payment_response_includes_remaining_balance(client, db_session):
    borrower = User(
        full_name="Payment Borrower",
        email="payment-borrower@example.com",
        password_hash="not-used",
        role="BORROWER",
    )
    product = LoanProduct(
        name="Payment Test Loan",
        interest_rate=Decimal("0.00"),
        min_amount=Decimal("100.00"),
        max_amount=Decimal("100.00"),
        max_term_months=2,
    )
    db_session.add_all([borrower, product])
    db_session.flush()

    application = LoanApplication(
        borrower_id=borrower.id,
        loan_product_id=product.id,
        requested_amount=Decimal("100.00"),
        requested_term_months=2,
        monthly_income=Decimal("1000.00"),
        status="APPROVED",
    )
    db_session.add(application)
    db_session.flush()

    loan = Loan(
        application_id=application.id,
        borrower_id=borrower.id,
        loan_product_id=product.id,
        principal_amount=Decimal("100.00"),
        interest_rate=Decimal("0.00"),
        term_months=2,
        outstanding_balance=Decimal("120.00"),
        status="ACTIVE",
    )
    db_session.add(loan)
    db_session.flush()
    db_session.add_all(
        [
            Installment(
                loan_id=loan.id,
                installment_number=number,
                due_date=datetime(2026, number, 1),
                amount_due=Decimal("60.00"),
                amount_paid=Decimal("0.00"),
                status="PENDING",
            )
            for number in (1, 2)
        ]
    )
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: borrower

    response = client.post(
        f"/loans/{loan.id}/payments",
        json={"amount": "25.00"},
        headers={"Idempotency-Key": "test-payment-remaining-balance-001"}
    )

    
    assert response.status_code == 201
    assert Decimal(response.json()["remaining_balance"]) == Decimal("95.00")



def test_full_payment_marks_loan_and_installments_paid(client, db_session):
    borrower = User(
        full_name="Full Payment Borrower",
        email="full-payment-borrower@example.com",
        password_hash="not-used",
        role="BORROWER",
    )
    product = LoanProduct(
        name="Full Payment Test Loan",
        interest_rate=Decimal("0.00"),
        min_amount=Decimal("100.00"),
        max_amount=Decimal("100.00"),
        max_term_months=2,
    )
    db_session.add_all([borrower, product])
    db_session.flush()

    application = LoanApplication(
        borrower_id=borrower.id,
        loan_product_id=product.id,
        requested_amount=Decimal("100.00"),
        requested_term_months=2,
        monthly_income=Decimal("1000.00"),
        status="APPROVED",
    )
    db_session.add(application)
    db_session.flush()

    loan = Loan(
        application_id=application.id,
        borrower_id=borrower.id,
        loan_product_id=product.id,
        principal_amount=Decimal("100.00"),
        interest_rate=Decimal("0.00"),
        term_months=2,
        outstanding_balance=Decimal("120.00"),
        status="ACTIVE",
    )
    db_session.add(loan)
    db_session.flush()

    installments = [
        Installment(
            loan_id=loan.id,
            installment_number=number,
            due_date=datetime(2026, number, 1),
            amount_due=Decimal("60.00"),
            amount_paid=Decimal("0.00"),
            status="PENDING",
        )
        for number in (1, 2)
    ]
    db_session.add_all(installments)
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: borrower

    response = client.post(
        f"/loans/{loan.id}/payments",
        json={"amount": "120.00"},
        headers={"Idempotency-Key": "test-full-payment-001"},
    )

    assert response.status_code == 201
    assert Decimal(response.json()["remaining_balance"]) == Decimal("0.00")

    saved_loan = db_session.query(Loan).filter(Loan.id == loan.id).first()

    assert saved_loan is not None
    assert saved_loan.status == "PAID"
    assert saved_loan.outstanding_balance == Decimal("0.00")

    saved_installments = (
        db_session.query(Installment)
        .filter(Installment.loan_id == loan.id)
        .order_by(Installment.installment_number)
        .all()
    )

    assert len(saved_installments) == 2

    for installment in saved_installments:
        assert installment.status == "PAID"
        assert installment.amount_paid == Decimal("60.00")



def test_overpayment_is_rejected(client, db_session):
    borrower = User(
        full_name="Overpayment Borrower",
        email="overpayment-borrower@example.com",
        password_hash="not-used",
        role="BORROWER",
    )
    product = LoanProduct(
        name="Overpayment Test Loan",
        interest_rate=Decimal("0.00"),
        min_amount=Decimal("100.00"),
        max_amount=Decimal("100.00"),
        max_term_months=2,
    )
    db_session.add_all([borrower, product])
    db_session.flush()

    application = LoanApplication(
        borrower_id=borrower.id,
        loan_product_id=product.id,
        requested_amount=Decimal("100.00"),
        requested_term_months=2,
        monthly_income=Decimal("1000.00"),
        status="APPROVED",
    )
    db_session.add(application)
    db_session.flush()

    loan = Loan(
        application_id=application.id,
        borrower_id=borrower.id,
        loan_product_id=product.id,
        principal_amount=Decimal("100.00"),
        interest_rate=Decimal("0.00"),
        term_months=2,
        outstanding_balance=Decimal("120.00"),
        status="ACTIVE",
    )
    db_session.add(loan)
    db_session.flush()

    db_session.add_all([
        Installment(
            loan_id=loan.id,
            installment_number=number,
            due_date=datetime(2026, number, 1),
            amount_due=Decimal("60.00"),
            amount_paid=Decimal("0.00"),
            status="PENDING",
        )
        for number in (1, 2)
    ])
    db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: borrower

    response = client.post(
        f"/loans/{loan.id}/payments",
        json={"amount": "120.01"},
        headers={"Idempotency-Key": "test-overpayment-001"},
    )

    assert response.status_code == 422

    saved_loan = db_session.query(Loan).filter(Loan.id == loan.id).first()
    assert saved_loan.outstanding_balance == Decimal("120.00")
    assert saved_loan.status == "ACTIVE"


def test_repeated_payment_request_does_not_charge_twice(client, db_session):
    borrower = User(
        full_name="Idempotency Borrower",
        email="idempotency-borrower@example.com",
        password_hash="not-used",
        role="BORROWER",
    )
    product = LoanProduct(
        name="Idempotency Test Loan",
        interest_rate=Decimal("0.00"),
        min_amount=Decimal("100.00"),
        max_amount=Decimal("100.00"),
        max_term_months=2,
    )
    db_session.add_all([borrower, product])
    db_session.flush()

    application = LoanApplication(
        borrower_id=borrower.id,
        loan_product_id=product.id,
        requested_amount=Decimal("100.00"),
        requested_term_months=2,
        monthly_income=Decimal("1000.00"),
        status="APPROVED",
    )
    db_session.add(application)
    db_session.flush()

    loan = Loan(
        application_id=application.id,
        borrower_id=borrower.id,
        loan_product_id=product.id,
        principal_amount=Decimal("100.00"),
        interest_rate=Decimal("0.00"),
        term_months=2,
        outstanding_balance=Decimal("120.00"),
        status="ACTIVE",
    )
    db_session.add(loan)
    db_session.flush()

    db_session.add_all([
        Installment(
            loan_id=loan.id,
            installment_number=number,
            due_date=datetime(2026, number, 1),
            amount_due=Decimal("60.00"),
            amount_paid=Decimal("0.00"),
            status="PENDING",
        )
        for number in (1, 2)
    ])
    db_session.commit()

    borrower_id = borrower.id

    app.dependency_overrides[get_current_user] = (
    lambda: type("TestUser", (), {"id": borrower_id, "role": "BORROWER"})()
    )

    headers = {"Idempotency-Key": "test-idempotency-retry-001"}
    payload = {"amount": "25.00"}

    first_response = client.post(
        f"/loans/{loan.id}/payments",
        json=payload,
        headers=headers,
    )
    second_response = client.post(
        f"/loans/{loan.id}/payments",
        json=payload,
        headers=headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert first_response.json()["id"] == second_response.json()["id"]

    saved_loan = db_session.query(Loan).filter(Loan.id == loan.id).first()
    assert saved_loan.outstanding_balance == Decimal("95.00")

    payments = db_session.query(Repayment).filter(
        Repayment.loan_id == loan.id
    ).all()
    assert len(payments) == 1



def test_borrower_cannot_pay_another_borrowers_loan(client, db_session):
    borrower_a = User(
        full_name="Loan Owner",
        email="loan-owner@example.com",
        password_hash="not-used",
        role="BORROWER",
    )
    borrower_b = User(
        full_name="Other Borrower",
        email="other-borrower@example.com",
        password_hash="not-used",
        role="BORROWER",
    )
    product = LoanProduct(
        name="Authorization Test Loan",
        interest_rate=Decimal("0.00"),
        min_amount=Decimal("100.00"),
        max_amount=Decimal("100.00"),
        max_term_months=2,
    )
    db_session.add_all([borrower_a, borrower_b, product])
    db_session.flush()

    application = LoanApplication(
        borrower_id=borrower_a.id,
        loan_product_id=product.id,
        requested_amount=Decimal("100.00"),
        requested_term_months=2,
        monthly_income=Decimal("1000.00"),
        status="APPROVED",
    )
    db_session.add(application)
    db_session.flush()

    loan = Loan(
        application_id=application.id,
        borrower_id=borrower_a.id,
        loan_product_id=product.id,
        principal_amount=Decimal("100.00"),
        interest_rate=Decimal("0.00"),
        term_months=2,
        outstanding_balance=Decimal("120.00"),
        status="ACTIVE",
    )
    db_session.add(loan)
    db_session.flush()

    db_session.add_all([
        Installment(
            loan_id=loan.id,
            installment_number=number,
            due_date=datetime(2026, number, 1),
            amount_due=Decimal("60.00"),
            amount_paid=Decimal("0.00"),
            status="PENDING",
        )
        for number in (1, 2)
    ])
    db_session.commit()

    borrower_b_id = borrower_b.id
    app.dependency_overrides[get_current_user] = (
        lambda: type(
            "TestUser",
            (),
            {"id": borrower_b_id, "role": "BORROWER"},
        )()
    )

    response = client.post(
        f"/loans/{loan.id}/payments",
        json={"amount": "25.00"},
        headers={"Idempotency-Key": "test-unauthorized-payment-001"},
    )

    assert response.status_code == 403

    saved_loan = db_session.query(Loan).filter(Loan.id == loan.id).first()
    assert saved_loan.outstanding_balance == Decimal("120.00")

    payments = db_session.query(Repayment).filter(
        Repayment.loan_id == loan.id
    ).all()
    assert len(payments) == 0


def test_retrying_full_payment_does_not_charge_twice(client, db_session):
    borrower = User(
        full_name="Full Retry Borrower",
        email="full-retry-borrower@example.com",
        password_hash="not-used",
        role="BORROWER",
    )
    product = LoanProduct(
        name="Full Retry Test Loan",
        interest_rate=Decimal("0.00"),
        min_amount=Decimal("100.00"),
        max_amount=Decimal("100.00"),
        max_term_months=2,
    )
    db_session.add_all([borrower, product])
    db_session.flush()

    application = LoanApplication(
        borrower_id=borrower.id,
        loan_product_id=product.id,
        requested_amount=Decimal("100.00"),
        requested_term_months=2,
        monthly_income=Decimal("1000.00"),
        status="APPROVED",
    )
    db_session.add(application)
    db_session.flush()

    loan = Loan(
        application_id=application.id,
        borrower_id=borrower.id,
        loan_product_id=product.id,
        principal_amount=Decimal("100.00"),
        interest_rate=Decimal("0.00"),
        term_months=2,
        outstanding_balance=Decimal("120.00"),
        status="ACTIVE",
    )
    db_session.add(loan)
    db_session.flush()

    db_session.add_all([
        Installment(
            loan_id=loan.id,
            installment_number=number,
            due_date=datetime(2026, number, 1),
            amount_due=Decimal("60.00"),
            amount_paid=Decimal("0.00"),
            status="PENDING",
        )
        for number in (1, 2)
    ])
    db_session.commit()

    borrower_id = borrower.id
    app.dependency_overrides[get_current_user] = (
        lambda: type(
            "TestUser",
            (),
            {"id": borrower_id, "role": "BORROWER"},
        )()
    )

    headers = {"Idempotency-Key": "test-full-payment-retry-001"}
    payload = {"amount": "120.00"}

    first_response = client.post(
        f"/loans/{loan.id}/payments",
        json=payload,
        headers=headers,
    )
    second_response = client.post(
        f"/loans/{loan.id}/payments",
        json=payload,
        headers=headers,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert first_response.json()["id"] == second_response.json()["id"]
    assert Decimal(second_response.json()["remaining_balance"]) == Decimal("0.00")

    saved_loan = db_session.query(Loan).filter(Loan.id == loan.id).first()
    assert saved_loan.status == "PAID"
    assert saved_loan.outstanding_balance == Decimal("0.00")

    payments = db_session.query(Repayment).filter(
        Repayment.loan_id == loan.id
    ).all()
    assert len(payments) == 1

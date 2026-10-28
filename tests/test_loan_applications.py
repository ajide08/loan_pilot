from app.models import Loan, Installment
from app.models import User, LoanProduct
from app.security import create_access_token
from decimal import Decimal


def create_borrower_token(db_session):
    borrower = User(
        full_name="Test Borrower",
        email="borrower@example.com",
        password_hash="unused-password-hash",
        role="BORROWER",
    )
    db_session.add(borrower)
    db_session.commit()
    db_session.refresh(borrower)
    return create_access_token(borrower.id)


def create_active_product(db_session):
    product = LoanProduct(
        name="Personal Loan",
        interest_rate=12,
        min_amount=50000,
        max_amount=1000000,
        max_term_months=12,
        active=True,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def application_payload(product_id, **overrides):
    payload = {
        "loan_product_id": product_id,
        "requested_amount": 500000,
        "requested_term_months": 12,
        "monthly_income": 200000,
    }
    payload.update(overrides)
    return payload


def test_borrower_can_create_application(client, db_session):
    token = create_borrower_token(db_session)
    product = create_active_product(db_session)

    response = client.post(
        "/loan-applications",
        headers={"Authorization": f"Bearer {token}"},
        json=application_payload(product.id),
    )

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"


def test_application_rejects_missing_product(client, db_session):
    token = create_borrower_token(db_session)

    response = client.post(
        "/loan-applications",
        headers={"Authorization": f"Bearer {token}"},
        json=application_payload(99999),
    )

    assert response.status_code == 404


def test_borrower_cannot_submit_second_pending_application(
    client, db_session
):
    token = create_borrower_token(db_session)
    product = create_active_product(db_session)
    product_id = product.id
    headers = {"Authorization": f"Bearer {token}"}

    first_response = client.post(
        "/loan-applications",
        headers=headers,
        json=application_payload(product_id),
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/loan-applications",
        headers=headers,
        json=application_payload(product_id),
    )

    assert second_response.status_code == 409


def test_application_rejects_amount_below_minimum(client, db_session):
    token = create_borrower_token(db_session)
    product = create_active_product(db_session)
    product_id = product.id

    response = client.post(
        "/loan-applications",
        headers={"Authorization": f"Bearer {token}"},
        json=application_payload(product_id, requested_amount=10000),
    )

    assert response.status_code == 422


def test_application_rejects_amount_above_maximum(client, db_session):
    token = create_borrower_token(db_session)
    product = create_active_product(db_session)
    product_id = product.id

    response = client.post(
        "/loan-applications",
        headers={"Authorization": f"Bearer {token}"},
        json=application_payload(product_id, requested_amount=1500000),
    )

    assert response.status_code == 422


def test_application_rejects_term_above_maximum(client, db_session):
    token = create_borrower_token(db_session)
    product = create_active_product(db_session)
    product_id = product.id

    response = client.post(
        "/loan-applications",
        headers={"Authorization": f"Bearer {token}"},
        json=application_payload(product_id, requested_term_months=18),
    )

    assert response.status_code == 422


def test_application_rejects_inactive_product(client, db_session):
    token = create_borrower_token(db_session)
    product = create_active_product(db_session)
    product_id = product.id

    # Mark the product inactive before submitting the request.
    product.active = False
    db_session.commit()

    response = client.post(
        "/loan-applications",
        headers={"Authorization": f"Bearer {token}"},
        json=application_payload(product_id),
    )

    assert response.status_code == 404


def test_borrower_cannot_access_another_borrowers_application(
    client, db_session
):
    first_token = create_borrower_token(db_session)
    product = create_active_product(db_session)
    product_id = product.id

    created = client.post(
        "/loan-applications",
        headers={"Authorization": f"Bearer {first_token}"},
        json=application_payload(product_id),
    )
    assert created.status_code == 201
    application_id = created.json()["id"]

    # Register a second borrower and obtain their token.
    registration = client.post(
        "/auth/register",
        json={
            "full_name": "Second Borrower",
            "email": "second.borrower@example.com",
            "password": "securepassword123",
        },
    )
    assert registration.status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": "second.borrower@example.com",
            "password": "securepassword123",
        },
    )
    assert login.status_code == 200
    second_token = login.json()["access_token"]

    response = client.get(
        f"/loan-applications/{application_id}",
        headers={"Authorization": f"Bearer {second_token}"},
    )

    assert response.status_code == 403




def test_approval_creates_loan_and_repayment_schedule(
    client, db_session
):
    borrower_token = create_borrower_token(db_session)
    product = create_active_product(db_session)
    product_id = product.id

    application_response = client.post(
        "/loan-applications",
        headers={"Authorization": f"Bearer {borrower_token}"},
        json=application_payload(product_id),
    )
    assert application_response.status_code == 201
    application_id = application_response.json()["id"]

    # Create a lending officer who can make the decision.
    officer = User(
        full_name="Test Officer",
        email="officer@example.com",
        password_hash="unused-password-hash",
        role="LENDING_OFFICER",
    )
    db_session.add(officer)
    db_session.commit()
    db_session.refresh(officer)

    officer_token = create_access_token(officer.id)

    response = client.post(
    f"/loan-applications/{application_id}/decision",
    headers={"Authorization": f"Bearer {officer_token}"},
    json={"decision": "APPROVE"},
)

    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    assert response.status_code == 200
    assert response.json()["application_status"] == "APPROVED"
    assert response.json()["loan_status"] == "ACTIVE"

    loan = (
        db_session.query(Loan)
        .filter(Loan.application_id == application_id)
        .first()
    )
    assert loan is not None

    installments = (
        db_session.query(Installment)
        .filter(Installment.loan_id == loan.id)
        .order_by(Installment.installment_number)
        .all()
    )

    assert len(installments) == 12
    assert all(item.status == "PENDING" for item in installments)
    assert sum(
        (item.amount_due for item in installments),
        Decimal("0.00"),
    ) == loan.outstanding_balance

def test_approval_request_body_is_parsed(client, db_session):
    from app.schemas import ApplicationDecision

    decision = ApplicationDecision.model_validate(
        {"decision": "APPROVE"}
    )
    assert decision.decision == "APPROVE"


def test_rejection_does_not_create_loan(client, db_session):
    from app.models import Loan

    borrower_token = create_borrower_token(db_session)
    product = create_active_product(db_session)
    product_id = product.id

    application_response = client.post(
        "/loan-applications",
        headers={"Authorization": f"Bearer {borrower_token}"},
        json=application_payload(product_id),
    )

    assert application_response.status_code == 201
    application_id = application_response.json()["id"]

    officer = User(
        full_name="Test Officer",
        email="officer@example.com",
        password_hash="unused-password-hash",
        role="LENDING_OFFICER",
    )
    db_session.add(officer)
    db_session.commit()
    db_session.refresh(officer)

    officer_token = create_access_token(officer.id)

    response = client.post(
        f"/loan-applications/{application_id}/decision",
        headers={"Authorization": f"Bearer {officer_token}"},
        json={
            "decision": "REJECT",
            "rejection_reason": "Income does not meet the lending criteria",
        },
    )

    print("REJECTION RESPONSE:", response.json())

    assert response.status_code == 200

    loan = (
        db_session.query(Loan)
        .filter(Loan.application_id == application_id)
        .first()
    )
    assert loan is None


def test_cannot_decide_application_twice(client, db_session):
    borrower_token = create_borrower_token(db_session)
    product = create_active_product(db_session)
    product_id = product.id

    application_response = client.post(
        "/loan-applications",
        headers={"Authorization": f"Bearer {borrower_token}"},
        json=application_payload(product_id),
    )
    assert application_response.status_code == 201
    application_id = application_response.json()["id"]

    officer = User(
        full_name="Test Officer",
        email="officer@example.com",
        password_hash="unused-password-hash",
        role="LENDING_OFFICER",
    )
    db_session.add(officer)
    db_session.commit()
    db_session.refresh(officer)
    officer_token = create_access_token(officer.id)

    headers = {"Authorization": f"Bearer {officer_token}"}

    first_response = client.post(
        f"/loan-applications/{application_id}/decision",
        headers=headers,
        json={
            "decision": "REJECT",
            "rejection_reason": "Income does not meet lending criteria",
        },
    )
    assert first_response.status_code == 200

    second_response = client.post(
        f"/loan-applications/{application_id}/decision",
        headers=headers,
        json={"decision": "APPROVE"},
    )

    assert second_response.status_code == 409

from decimal import Decimal

from app.models import LoanApplication, LoanProduct, User
from app.security import verify_password


def register_user(client, full_name, email, password="password123", role="BORROWER"):
    payload = {
        "full_name": full_name,
        "email": email,
        "password": password,
    }
    if role is not None:
        payload["role"] = role
    return client.post("/auth/register", json=payload)


def login_user(client, email, password="password123"):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )


def create_product(db_session, *, name="Starter Loan", min_amount=1000, max_amount=5000, max_term_months=12, active=True):
    product = LoanProduct(
        name=name,
        interest_rate=Decimal("5.5"),
        min_amount=Decimal(str(min_amount)),
        max_amount=Decimal(str(max_amount)),
        max_term_months=max_term_months,
        active=active,
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


def test_register_user(client):
    response = register_user(client, "Test User", "test@example.com")
    assert response.status_code == 201


def test_password_is_hashed(client, db_session):
    response = register_user(client, "Test User", "test@example.com")
    assert response.status_code == 201

    user = db_session.query(User).filter(User.email == "test@example.com").first()
    assert user is not None
    assert user.password_hash != "password123"
    assert verify_password("password123", user.password_hash)


def test_login(client):
    register_user(client, "Test User", "test@example.com")

    response = login_user(client, "test@example.com")
    payload = response.json()
    assert response.status_code == 200
    assert "access_token" in payload
    assert payload["user"]["email"] == "test@example.com"
    assert payload["user"]["full_name"] == "Test User"


def test_invalid_token(client):
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


def test_borrower_cannot_access_admin(client):
    register_user(client, "Borrower", "borrower@example.com")
    token = login_user(client, "borrower@example.com").json()["access_token"]

    response = client.get(
        "/admin/test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_borrower_can_submit_valid_application_and_receives_201(client, db_session):
    register_user(client, "Borrower", "borrower@example.com")
    token = login_user(client, "borrower@example.com").json()["access_token"]
    product = create_product(db_session)

    response = client.post(
        "/loan-applications",
        json={
            "loan_product_id": product.id,
            "requested_amount": 2500,
            "requested_term_months": 12,
            "monthly_income": 5000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    assert response.json()["borrower_id"] == 1
    assert db_session.query(LoanApplication).count() == 1


def test_requested_amount_below_product_minimum_is_rejected(client, db_session):
    register_user(client, "Borrower", "borrower@example.com")
    token = login_user(client, "borrower@example.com").json()["access_token"]
    product = create_product(db_session, min_amount=1000, max_amount=5000)

    response = client.post(
        "/loan-applications",
        json={
            "loan_product_id": product.id,
            "requested_amount": 900,
            "requested_term_months": 12,
            "monthly_income": 5000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert db_session.query(LoanApplication).count() == 0


def test_requested_amount_above_product_maximum_is_rejected(client, db_session):
    register_user(client, "Borrower", "borrower@example.com")
    token = login_user(client, "borrower@example.com").json()["access_token"]
    product = create_product(db_session, min_amount=1000, max_amount=5000)

    response = client.post(
        "/loan-applications",
        json={
            "loan_product_id": product.id,
            "requested_amount": 6000,
            "requested_term_months": 12,
            "monthly_income": 5000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert db_session.query(LoanApplication).count() == 0


def test_requested_term_above_product_maximum_is_rejected(client, db_session):
    register_user(client, "Borrower", "borrower@example.com")
    token = login_user(client, "borrower@example.com").json()["access_token"]
    product = create_product(db_session, min_amount=1000, max_amount=5000, max_term_months=12)

    response = client.post(
        "/loan-applications",
        json={
            "loan_product_id": product.id,
            "requested_amount": 2500,
            "requested_term_months": 24,
            "monthly_income": 5000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422
    assert db_session.query(LoanApplication).count() == 0


def test_inactive_or_nonexistent_product_is_rejected(client, db_session):
    register_user(client, "Borrower", "borrower@example.com")
    token = login_user(client, "borrower@example.com").json()["access_token"]
    product = create_product(db_session, active=False)

    inactive_response = client.post(
        "/loan-applications",
        json={
            "loan_product_id": product.id,
            "requested_amount": 2500,
            "requested_term_months": 12,
            "monthly_income": 5000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    missing_response = client.post(
        "/loan-applications",
        json={
            "loan_product_id": 999999,
            "requested_amount": 2500,
            "requested_term_months": 12,
            "monthly_income": 5000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert inactive_response.status_code == 404
    assert missing_response.status_code == 404
    assert db_session.query(LoanApplication).count() == 0


def test_second_pending_application_from_same_borrower_is_rejected(client, db_session):
    register_user(client, "Borrower", "borrower@example.com")
    token = login_user(client, "borrower@example.com").json()["access_token"]
    product = create_product(db_session)
    product_id = product.id

    first_response = client.post(
        "/loan-applications",
        json={
            "loan_product_id": product_id,
            "requested_amount": 2500,
            "requested_term_months": 12,
            "monthly_income": 5000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    second_response = client.post(
        "/loan-applications",
        json={
            "loan_product_id": product_id,
            "requested_amount": 3000,
            "requested_term_months": 12,
            "monthly_income": 5000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert db_session.query(LoanApplication).count() == 1


def test_borrower_can_retrieve_their_own_application(client, db_session):
    register_user(client, "Borrower", "borrower@example.com")
    token = login_user(client, "borrower@example.com").json()["access_token"]
    product = create_product(db_session)

    create_response = client.post(
        "/loan-applications",
        json={
            "loan_product_id": product.id,
            "requested_amount": 2500,
            "requested_term_months": 12,
            "monthly_income": 5000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    application_id = create_response.json()["id"]

    response = client.get(
        f"/loan-applications/{application_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == application_id


def test_borrower_cannot_retrieve_another_borrowers_application(client, db_session):
    register_user(client, "Borrower One", "borrower1@example.com")
    register_user(client, "Borrower Two", "borrower2@example.com")
    borrower_one_token = login_user(client, "borrower1@example.com").json()["access_token"]
    borrower_two_token = login_user(client, "borrower2@example.com").json()["access_token"]
    product = create_product(db_session)

    create_response = client.post(
        "/loan-applications",
        json={
            "loan_product_id": product.id,
            "requested_amount": 2500,
            "requested_term_months": 12,
            "monthly_income": 5000,
        },
        headers={"Authorization": f"Bearer {borrower_one_token}"},
    )
    application_id = create_response.json()["id"]

    response = client.get(
        f"/loan-applications/{application_id}",
        headers={"Authorization": f"Bearer {borrower_two_token}"},
    )

    assert response.status_code == 403


def test_unauthenticated_request_is_rejected(client, db_session):
    product = create_product(db_session)

    response = client.post(
        "/loan-applications",
        json={
            "loan_product_id": product.id,
            "requested_amount": 2500,
            "requested_term_months": 12,
            "monthly_income": 5000,
        },
    )

    assert response.status_code == 401
    assert db_session.query(LoanApplication).count() == 0
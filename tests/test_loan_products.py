
from app.models import User
from app.security import create_access_token


def create_admin_token(db_session):
    admin = User(
        full_name="Test Admin",
        email="admin@example.com",
        password_hash="unused-password-hash",
        role="SYSTEM_ADMIN",
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    return create_access_token(admin.id)


def test_admin_can_create_loan_product(client, db_session):
    token = create_admin_token(db_session)

    response = client.post(
        "/loan-products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Personal Loan",
            "interest_rate": 5.0,
            "min_amount": 10000,
            "max_amount": 100000,
            "max_term_months": 12,
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Personal Loan"
    assert float(response.json()["min_amount"]) == 10000
    assert float(response.json()["max_amount"]) == 100000


def test_borrower_cannot_create_loan_product(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Test Borrower",
            "email": "borrower@example.com",
            "password": "securepassword123",
        },
    )
    assert response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": "borrower@example.com",
            "password": "securepassword123",
        },
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/loan-products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Personal Loan",
            "interest_rate": 5.0,
            "min_amount": 10000,
            "max_amount": 100000,
            "max_term_months": 12,
        },
    )

    assert response.status_code == 403


def create_product(client, token, name="Personal Loan"):
    return client.post(
        "/loan-products",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": name,
            "interest_rate": 5.0,
            "min_amount": 10000,
            "max_amount": 100000,
            "max_term_months": 12,
        },
    )


def test_anyone_can_list_loan_products(client, db_session):
    token = create_admin_token(db_session)
    create_product(client, token)

    response = client.get("/loan-products")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Personal Loan"


def test_admin_can_update_loan_product(client, db_session):
    token = create_admin_token(db_session)
    created = create_product(client, token)
    product_id = created.json()["id"]

    response = client.patch(
        f"/loan-products/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"max_amount": 200000},
    )

    assert response.status_code == 200
    assert float(response.json()["max_amount"]) == 200000


def test_update_rejects_minimum_above_maximum(client, db_session):
    token = create_admin_token(db_session)
    created = create_product(client, token)
    product_id = created.json()["id"]

    response = client.patch(
        f"/loan-products/{product_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"min_amount": 150000},
    )

    assert response.status_code == 422


def test_update_nonexistent_product_returns_404(client, db_session):
    token = create_admin_token(db_session)

    response = client.patch(
        "/loan-products/99999",
        headers={"Authorization": f"Bearer {token}"},
        json={"max_amount": 200000},
    )

    assert response.status_code == 404


def test_duplicate_product_name_returns_409(client, db_session):
    token = create_admin_token(db_session)
    create_product(client, token)

    response = create_product(client, token)

    assert response.status_code == 409


def test_borrower_cannot_update_loan_product(client):
    client.post(
        "/auth/register",
        json={
            "full_name": "Test Borrower",
            "email": "borrower@example.com",
            "password": "securepassword123",
        },
    )
    login = client.post(
        "/auth/login",
        json={
            "email": "borrower@example.com",
            "password": "securepassword123",
        },
    )
    token = login.json()["access_token"]

    response = client.patch(
        "/loan-products/1",
        headers={"Authorization": f"Bearer {token}"},
        json={"max_amount": 200000},
    )

    assert response.status_code == 403

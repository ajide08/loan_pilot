
from app.models import User
from app.security import verify_password


def test_register_user(client, db_session):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Test Borrower",
            "email": "borrower@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "borrower@example.com"


def test_registration_hashes_password(client, db_session):
    password = "StrongPassword123!"

    response = client.post(
        "/auth/register",
        json={
            "full_name": "Hash Test",
            "email": "hash@example.com",
            "password": password,
        },
    )

    assert response.status_code == 201

    user = (
        db_session.query(User)
        .filter(User.email == "hash@example.com")
        .first()
    )

    assert user is not None
    assert user.password_hash != password
    assert verify_password(password, user.password_hash)


def test_registration_defaults_to_borrower(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Regular User",
            "email": "regular@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 201

    user_response = response.json()
    assert "role" not in user_response


def test_registration_rejects_admin_role(client, db_session):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Malicious User",
            "email": "malicious@example.com",
            "password": "StrongPassword123!",
            "role": "SYSTEM_ADMIN",
        },
    )

    user = (
        db_session.query(User)
        .filter(User.email == "malicious@example.com")
        .first()
)

    assert user is not None
    assert user.role == "BORROWER"

    assert response.status_code == 201

    user_response = response.json()
    assert user_response["email"] == "malicious@example.com"


def test_login_with_valid_credentials(client):
    client.post(
        "/auth/register",
        json={
            "full_name": "Login Test",
            "email": "login@example.com",
            "password": "StrongPassword123!",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"


def test_login_rejects_wrong_password(client):
    client.post(
        "/auth/register",
        json={
            "full_name": "Wrong Password Test",
            "email": "wrong-password@example.com",
            "password": "StrongPassword123!",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "wrong-password@example.com",
            "password": "IncorrectPassword123!",
        },
    )

    assert response.status_code == 401


def test_login_rejects_unknown_email(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "StrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_registration_rejects_duplicate_email(client):
    payload = {
        "full_name": "Duplicate Test",
        "email": "duplicate@example.com",
        "password": "StrongPassword123!",
    }

    first_response = client.post("/auth/register", json=payload)
    second_response = client.post("/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409

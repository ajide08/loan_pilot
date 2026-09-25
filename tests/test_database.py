from app.models import User
from app.security import verify_password


def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 201


def test_password_is_hashed(client, db_session):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 201

    user = (
        db_session.query(User)
        .filter(User.email == "test@example.com")
        .first()
    )

    assert user is not None
    assert user.password_hash != "password123"
    assert verify_password("password123", user.password_hash)


def test_login(client):
    client.post(
        "/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "password123",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123",
        },
    )
    payload = response.json()
    assert response.status_code == 200
    assert "access_token" in payload
    assert payload["user"]["email"] == "test@example.com"
    assert payload["user"]["full_name"] == "Test User"


def test_invalid_token(client):
    response = client.get(
        "/users/me",
        headers={
            "Authorization": "Bearer invalid_token"
        },
    )
    assert response.status_code == 401


def test_borrower_cannot_access_admin(client):
    client.post(
        "/auth/register",
        json={
            "full_name": "Borrower",
            "email": "borrower@example.com",
            "password": "password123",
        },
    )

    login_response = client.post(
        "/auth/login",
        json={
            "email": "borrower@example.com",
            "password": "password123",
        },
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/admin/test",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )
    assert response.status_code == 403
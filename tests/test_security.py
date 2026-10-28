
from app.models import User


def register_borrower(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Test Borrower",
            "email": "borrower@example.com",
            "password": "securepassword123",
        },
    )
    assert response.status_code == 201


def login_borrower(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "borrower@example.com",
            "password": "securepassword123",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/admin/test",
        headers={"Authorization": "Bearer invalid.token.here"},
    )

    assert response.status_code == 401


def test_borrower_cannot_access_admin_endpoint(client):
    register_borrower(client)
    token = login_borrower(client)

    response = client.get(
        "/admin/test",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_can_access_admin_endpoint(client, db_session):
    admin = User(
        full_name="Test Admin",
        email="admin@example.com",
        password_hash="unused-password-hash",
        role="SYSTEM_ADMIN",
    )
    db_session.add(admin)
    db_session.commit()

    from app.security import create_access_token

    token = create_access_token(admin.id)

    response = client.get(
        "/admin/test",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["msg"] == "Admin access granted"
    assert response.json()["user"] == "Test Admin"

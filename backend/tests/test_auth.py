from __future__ import annotations

from tests.conftest import PASSWORD


def test_register_creates_user_and_session(world, client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "new@example.com",
            "username": "newuser",
            "display_name": "Новый",
            "password": "NewUser123!",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["user"]["username"] == "newuser"
    assert payload["user"]["role"] == "user"
    assert "tube_access_token" in response.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["username"] == "newuser"


def test_register_rejects_duplicate_username(world, client):
    response = client.post(
        "/api/auth/register",
        json={"email": "other@example.com", "username": "user", "password": "NewUser123!"},
    )
    assert response.status_code == 409
    assert "занято" in response.json()["detail"]


def test_register_rejects_duplicate_email(world, client):
    response = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "username": "another", "password": "NewUser123!"},
    )
    assert response.status_code == 409


def test_login_by_username_and_email(world, make_client):
    for login_value in ("user", "user@example.com"):
        client = make_client()
        response = client.post(
            "/api/auth/login",
            json={"login": login_value, "password": PASSWORD},
        )
        assert response.status_code == 200, response.text
        assert response.json()["user"]["username"] == "user"


def test_login_rejects_wrong_password(world, client):
    response = client.post("/api/auth/login", json={"login": "user", "password": "wrong-pass"})
    assert response.status_code == 401
    assert "Неверный" in response.json()["detail"]


def test_me_requires_authentication(world, client):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_session(world, login):
    client = login("user")
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_update_profile(world, login):
    client = login("user")
    response = client.patch(
        "/api/auth/me",
        json={"display_name": "Новое имя", "bio": "Новое описание"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["display_name"] == "Новое имя"
    assert response.json()["user"]["bio"] == "Новое описание"


def test_oauth2_token_flow(world, client):
    response = client.post(
        "/api/auth/token",
        data={"username": "admin", "password": PASSWORD},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user"]["role"] == "admin"

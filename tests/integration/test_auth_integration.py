"""
Integration tests for auth endpoints.

Unlike the unit tests, these go through the real FastAPI app + a real
(test) Postgres database via the `client` fixture in conftest.py.
"""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_signup_creates_user(client):
    response = await client.post(
        "v1/signup",
        json={"email": "alice@example.com", "password": "strongpassword123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert "id" in body


@pytest.mark.asyncio
async def test_signup_duplicate_email_rejected(client):
    payload = {"email": "bob@example.com", "password": "strongpassword123"}
    first = await client.post("v1/signup", json=payload)
    assert first.status_code == 201

    second = await client.post("/signup", json=payload)
    assert second.status_code == 400  # or 409, depending on your API design


@pytest.mark.asyncio
async def test_login_with_correct_credentials_returns_tokens(client):
    await client.post(
        "v1/signup",
        json={"email": "carol@example.com", "password": "strongpassword123"},
    )
    response = await client.post(
        "v1/login",
        json={"email": "carol@example.com", "password": "strongpassword123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_login_with_wrong_password_rejected(client):
    await client.post(
        "v1/signup",
        json={"email": "dave@example.com", "password": "strongpassword123"},
    )
    response = await client.post(
        "v1/login",
        json={"email": "dave@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_missing_token(client):
    response = await client.get("v1/auth/me")  # adjust to your actual protected route
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_accepts_valid_token(client):
    await client.post(
        "v1/signup",
        json={"email": "erin@example.com", "password": "strongpassword123"},
    )
    login = await client.post(
        "v1/login",
        json={"email": "erin@example.com", "password": "strongpassword123"},
    )
    token = login.json()["access_token"]

    response = await client.get(
        "v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "erin@example.com"

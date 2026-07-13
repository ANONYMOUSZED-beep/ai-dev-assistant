"""Tests for registration, login, and token-protected access (SQLite-backed)."""

from __future__ import annotations

from app.core.auth import hash_password, verify_password
from httpx import AsyncClient

# asyncio_mode=auto runs async tests automatically; this module also has a sync
# test, so no module-level asyncio mark.


def test_password_hash_roundtrip() -> None:
    h = hash_password("s3cret-password")
    assert h != "s3cret-password"
    assert verify_password("s3cret-password", h) is True
    assert verify_password("wrong", h) is False


async def test_register_returns_token(db_client: AsyncClient) -> None:
    resp = await db_client.post(
        "/api/v1/auth/register", json={"username": "alice", "password": "hunter2"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["username"] == "alice"
    assert body["access_token"]


async def test_duplicate_username_rejected(db_client: AsyncClient) -> None:
    payload = {"username": "bob", "password": "hunter2"}
    first = await db_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    dup = await db_client.post("/api/v1/auth/register", json=payload)
    assert dup.status_code == 422
    assert dup.json()["error"]["code"] == "validation_error"


async def test_login_and_me_flow(db_client: AsyncClient) -> None:
    await db_client.post(
        "/api/v1/auth/register", json={"username": "carol", "password": "hunter2"}
    )

    bad = await db_client.post(
        "/api/v1/auth/login", json={"username": "carol", "password": "nope"}
    )
    assert bad.status_code == 401

    ok = await db_client.post(
        "/api/v1/auth/login", json={"username": "carol", "password": "hunter2"}
    )
    assert ok.status_code == 200
    token = ok.json()["access_token"]

    # /me requires the token.
    unauth = await db_client.get("/api/v1/auth/me")
    assert unauth.status_code == 401

    me = await db_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == "carol"


async def test_protected_endpoint_accepts_valid_token(db_client: AsyncClient) -> None:
    reg = await db_client.post(
        "/api/v1/auth/register", json={"username": "dave", "password": "hunter2"}
    )
    token = reg.json()["access_token"]
    resp = await db_client.post(
        "/api/v1/chat",
        json={"question": "How does FastAPI work?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["provider"] == "fake"


async def test_google_sign_in_creates_and_reuses_account(
    db_client: AsyncClient, monkeypatch
) -> None:
    """Google sign-in creates a passwordless account, then reuses it on repeat."""
    import app.api.v1.auth as auth_module

    def fake_verify(credential: str) -> dict:
        assert credential == "fake-google-credential"
        return {"sub": "google-123", "email": "Grace@example.com", "name": "Grace"}

    monkeypatch.setattr(auth_module, "verify_google_id_token", fake_verify)

    first = await db_client.post(
        "/api/v1/auth/google", json={"credential": "fake-google-credential"}
    )
    assert first.status_code == 200
    body = first.json()
    assert body["access_token"]
    username = body["username"]
    assert username  # derived from the email local part

    # Signing in again with the same Google account returns the same username.
    second = await db_client.post(
        "/api/v1/auth/google", json={"credential": "fake-google-credential"}
    )
    assert second.status_code == 200
    assert second.json()["username"] == username


async def test_google_sign_in_rejects_invalid_token(
    db_client: AsyncClient, monkeypatch
) -> None:
    import app.api.v1.auth as auth_module

    def boom(credential: str) -> dict:
        raise ValueError("bad token")

    monkeypatch.setattr(auth_module, "verify_google_id_token", boom)

    resp = await db_client.post(
        "/api/v1/auth/google", json={"credential": "whatever"}
    )
    assert resp.status_code == 401

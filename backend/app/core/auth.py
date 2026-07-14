"""Password hashing (bcrypt), JWT access-token helpers, and Google ID-token verify."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from jwt import PyJWKClient

from app.core.config import get_settings

# bcrypt only uses the first 72 bytes of a password; truncate consistently so
# longer inputs don't raise and hash/verify stay in agreement.
_MAX_BCRYPT_BYTES = 72


def hash_password(password: str) -> str:
    """Hash a plaintext password with a per-hash random salt."""
    pw = password.encode("utf-8")[:_MAX_BCRYPT_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time check of a plaintext password against a stored hash."""
    try:
        pw = password.encode("utf-8")[:_MAX_BCRYPT_BYTES]
        return bcrypt.checkpw(pw, password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, *, guest: bool = False) -> str:
    """Create a signed JWT whose ``sub`` claim is the user id."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()
        ),
    }
    if guest:
        payload["guest"] = True
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str | None:
    """Return the ``sub`` (user id) from a valid token, or None if invalid/expired."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None


def token_is_guest(token: str) -> bool:
    """Return True if the token is valid and carries a guest claim."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return False
    return payload.get("guest") is True


# ── Google Sign-In ───────────────────────────────────────────────
_GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
_jwk_client: PyJWKClient | None = None


def _google_jwk_client() -> PyJWKClient:
    """Cached JWKS client that fetches (and caches) Google's public signing keys."""
    global _jwk_client
    if _jwk_client is None:
        _jwk_client = PyJWKClient(_GOOGLE_CERTS_URL)
    return _jwk_client


def verify_google_id_token(credential: str) -> dict[str, Any]:
    """Verify a Google Identity Services ID token and return its claims.

    Validates the RS256 signature against Google's published keys, the audience
    (our configured client id), the expiry, and the issuer. Raises ``ValueError``
    if verification fails or Google sign-in isn't configured. This performs a
    network fetch of Google's certs on first use (then cached), so callers should
    run it off the event loop (e.g. via ``asyncio.to_thread``).
    """
    settings = get_settings()
    client_id = settings.google_client_id
    if not client_id:
        raise ValueError("Google sign-in is not configured")

    signing_key = _google_jwk_client().get_signing_key_from_jwt(credential)
    claims: dict[str, Any] = jwt.decode(
        credential,
        signing_key.key,
        algorithms=["RS256"],
        audience=client_id,
    )
    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise ValueError("Invalid token issuer")
    if not claims.get("sub") or not claims.get("email"):
        raise ValueError("Token missing required claims")
    return claims

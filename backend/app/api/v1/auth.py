"""Authentication endpoints: register, login, Google sign-in, and current-user."""

from __future__ import annotations

import asyncio
import re

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    hash_password,
    verify_google_id_token,
    verify_password,
)
from app.core.deps import CurrentUserDep, SessionDep
from app.core.exceptions import AuthError, ValidationError
from app.core.logging import get_logger
from app.db.models import User
from app.schemas.auth import (
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


async def _unique_username(session: AsyncSession, desired: str) -> str:
    """Return a username based on ``desired`` that is not already taken."""
    base = re.sub(r"[^a-z0-9_.-]", "", desired.lower()).strip("._-") or "user"
    base = base[:40]
    candidate = base
    suffix = 0
    while await session.scalar(select(User).where(User.username == candidate)):
        suffix += 1
        candidate = f"{base}{suffix}"
    return candidate


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(req: RegisterRequest, session: SessionDep) -> TokenResponse:
    """Create a new account and return an access token."""
    username = req.username.strip().lower()
    existing = await session.scalar(select(User).where(User.username == username))
    if existing is not None:
        raise ValidationError("Username is already taken")

    user = User(username=username, password_hash=hash_password(req.password))
    session.add(user)
    await session.commit()

    return TokenResponse(access_token=create_access_token(user.id), username=user.username)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, session: SessionDep) -> TokenResponse:
    """Verify credentials and return an access token."""
    username = req.username.strip().lower()
    user = await session.scalar(select(User).where(User.username == username))
    if (
        user is None
        or user.password_hash is None
        or not verify_password(req.password, user.password_hash)
    ):
        raise AuthError("Invalid username or password")

    return TokenResponse(access_token=create_access_token(user.id), username=user.username)


@router.post("/google", response_model=TokenResponse)
async def google_login(req: GoogleLoginRequest, session: SessionDep) -> TokenResponse:
    """Sign in (or sign up) with a Google ID token.

    Verifies the token, then finds the account by Google subject, links it to an
    existing account with the same email, or creates a new passwordless account.
    """
    try:
        claims = await asyncio.to_thread(verify_google_id_token, req.credential)
    except Exception as exc:  # noqa: BLE001 - surface a single clean auth error
        logger.warning("Google sign-in verification failed: %s", exc)
        raise AuthError("Google sign-in failed. Please try again.") from exc

    google_sub = str(claims["sub"])
    email = str(claims["email"]).lower()

    user = await session.scalar(select(User).where(User.google_sub == google_sub))
    if user is None:
        # Link to an existing account with the same email, if any.
        user = await session.scalar(select(User).where(User.email == email))
        if user is not None:
            user.google_sub = google_sub
        else:
            username = await _unique_username(session, email.split("@")[0])
            user = User(
                username=username,
                email=email,
                google_sub=google_sub,
                password_hash=None,
            )
            session.add(user)
    await session.commit()

    return TokenResponse(access_token=create_access_token(user.id), username=user.username)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUserDep) -> UserResponse:
    """Return the authenticated user."""
    return UserResponse(id=current_user.id, username=current_user.username)

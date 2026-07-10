"""Authentication endpoints: register, login, and current-user."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.core.auth import create_access_token, hash_password, verify_password
from app.core.deps import CurrentUserDep, SessionDep
from app.core.exceptions import AuthError, ValidationError
from app.db.models import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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
    if user is None or not verify_password(req.password, user.password_hash):
        raise AuthError("Invalid username or password")

    return TokenResponse(access_token=create_access_token(user.id), username=user.username)


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUserDep) -> UserResponse:
    """Return the authenticated user."""
    return UserResponse(id=current_user.id, username=current_user.username)

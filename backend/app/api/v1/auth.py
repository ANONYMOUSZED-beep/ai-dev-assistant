"""Authentication endpoints: register, login, Google sign-in, and current-user."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from fastapi import APIRouter
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    hash_password,
    verify_google_id_token,
    verify_password,
)
from app.core.deps import CurrentUserDep, RagDep, SessionDep
from app.core.exceptions import AuthError, ValidationError
from app.core.logging import get_logger
from app.db.models import Conversation, Message, Repository, User
from app.schemas.auth import (
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.conversation_service import ConversationService

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


@router.get("/me/export")
async def export_my_data(
    current_user: CurrentUserDep, session: SessionDep
) -> dict[str, Any]:
    """Return all of the current user's data (account, repositories, chats)."""
    repos = (
        await session.execute(
            select(Repository).where(Repository.user_id == current_user.id)
        )
    ).scalars().all()

    convo_service = ConversationService(session)
    summaries = await convo_service.list_summaries(current_user.id)
    conversations = []
    for summary in summaries:
        detail = await convo_service.get_detail(current_user.id, summary.id)
        if detail is not None:
            conversations.append(detail.model_dump(mode="json"))

    return {
        "account": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat(),
        },
        "repositories": [
            {
                "id": r.id,
                "url": r.url,
                "branch": r.branch,
                "status": r.status,
                "files_indexed": r.files_indexed,
                "chunks_indexed": r.chunks_indexed,
            }
            for r in repos
        ],
        "conversations": conversations,
    }


@router.delete("/me")
async def delete_account(
    current_user: CurrentUserDep, session: SessionDep, rag: RagDep
) -> dict[str, str]:
    """Permanently delete the current user's account and all of their data.

    Removes conversations/messages, repositories, and each repository's indexed
    vectors, then the account itself. Explicit deletes are used (rather than relying
    on cascade) so behaviour is identical on freshly-created and migrated schemas.
    """
    user_id = current_user.id

    # Purge each repository's vectors from the store, then the repository rows.
    repos = (
        await session.execute(
            select(Repository).where(Repository.user_id == user_id)
        )
    ).scalars().all()
    for repo in repos:
        try:
            await asyncio.to_thread(rag.delete_collection, repo.collection)
        except Exception:  # noqa: BLE001 - best-effort vector cleanup
            logger.warning("Failed to purge vectors for collection %s", repo.collection)
    await session.execute(delete(Repository).where(Repository.user_id == user_id))

    # Delete conversations and their messages.
    conv_ids = (
        await session.execute(
            select(Conversation.id).where(Conversation.user_id == user_id)
        )
    ).scalars().all()
    if conv_ids:
        await session.execute(
            delete(Message).where(Message.conversation_id.in_(conv_ids))
        )
        await session.execute(
            delete(Conversation).where(Conversation.user_id == user_id)
        )

    # Finally, the account.
    user = await session.get(User, user_id)
    if user is not None:
        await session.delete(user)
    await session.commit()

    logger.info("Deleted account %s and all associated data", user_id)
    return {"deleted": user_id}

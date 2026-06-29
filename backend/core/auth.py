from typing import Any

from backend.core.config import settings
from backend.core.db import get_db
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import Client, create_client

# Security schema
security = HTTPBearer()

# Initialize Supabase client (lazy — only used if SUPABASE_URL is configured)
_supabase_client: Client | None = None


def _get_supabase_client() -> Client | None:
    global _supabase_client
    if _supabase_client is None and settings.SUPABASE_URL:
        try:
            _supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        except Exception:
            pass
    return _supabase_client


class CurrentUser:
    """Authenticated user info."""

    def __init__(self, user_id: str, email: str, org_id: str, role: str):
        self.id = user_id
        self.email = email
        self.org_id = org_id
        self.role = role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """Extract and verify JWT token, returning the current user."""
    token = credentials.credentials
    user_id: str | None = None
    email: str | None = None

    # 1. Try to verify token using Supabase client
    sb_client = _get_supabase_client()
    if sb_client:
        try:
            sb_user = sb_client.auth.get_user(token)
            if sb_user and sb_user.user:
                user_id = sb_user.user.id
                email = sb_user.user.email
        except Exception:
            pass  # Fall through to local JWT decode

    # 2. Fallback to local JWT decode (hardcoded HS256 — never allow "none")
    if not user_id:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=["HS256"]
            )
            user_id = payload.get("sub")
            email = payload.get("email")
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Query user details from the database
    from backend.models.models import User

    result = await db.execute(select(User).where(User.id == user_id))
    db_user = result.scalars().first()

    if not db_user:
        # Generic message — no user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    return CurrentUser(
        user_id=str(db_user.id),
        email=db_user.email,
        org_id=str(db_user.org_id),
        role=db_user.role,
    )


def require_role(allowed_roles: list[str]) -> Any:
    """Role authorization check dependency."""
    def dependency(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return dependency

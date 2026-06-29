from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import CurrentUser, _get_supabase_client, get_current_user
from backend.core.config import settings
from backend.core.db import get_db
from backend.models.models import Organization, User
from backend.models.schemas import LoginRequest, RegisterRequest, Token
from backend.models.schemas import User as UserSchema

router = APIRouter()

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

# Rate limiter for auth endpoints
limiter = Limiter(key_func=get_remote_address)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Helper to generate JWT access token locally for fallbacks."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    # Always use HS256 — never configurable
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


@router.post("/register", response_model=Token)
@limiter.limit("5/minute")
async def register(
    request: Request,
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Register a new organization and administrator user."""
    # 1. Check if user already exists
    stmt = select(User).where(User.email == payload.email)
    res = await db.execute(stmt)
    existing_user = res.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address already registered.",
        )

    # 2. Try registering user in Supabase auth system
    supabase_uid = None
    sb_client = _get_supabase_client()
    if sb_client:
        try:
            sb_res = sb_client.auth.sign_up({
                "email": payload.email,
                "password": payload.password,
            })
            if sb_res and sb_res.user:
                supabase_uid = sb_res.user.id
        except Exception:
            pass

    # Fallback to local UID generation if Supabase client is not configured
    if not supabase_uid:
        import uuid
        supabase_uid = str(uuid.uuid4())

    # 3. Create local organization
    org = Organization(
        name=payload.org_name,
        sector=payload.sector,
        country=payload.country,
        plan="free"
    )
    db.add(org)
    await db.flush()  # Flush to populate org.id

    # 4. Create local user linked to organization and supabase UID
    #    SECURITY FIX: Always store bcrypt password hash for local auth fallback
    user = User(
        id=supabase_uid,
        org_id=org.id,
        email=payload.email,
        password_hash=_hash_password(payload.password),
        role="admin"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 5. Generate local fallback token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Verify user login against Supabase or fallback local password check."""
    # 1. Try to login via Supabase auth
    supabase_uid = None
    sb_client = _get_supabase_client()
    if sb_client:
        try:
            sb_res = sb_client.auth.sign_in_with_password({
                "email": payload.email,
                "password": payload.password
            })
            if sb_res and sb_res.user:
                supabase_uid = sb_res.user.id
        except Exception:
            pass

    # 2. Retrieve user from local DB
    if supabase_uid:
        stmt = select(User).where(User.id == supabase_uid)
    else:
        stmt = select(User).where(User.email == payload.email)

    res = await db.execute(stmt)
    user = res.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # 3. SECURITY FIX: If Supabase didn't authenticate, verify password locally
    #    Previously this was bypassed — any email would get a token without password check.
    if not supabase_uid and (not user.password_hash or not _verify_password(payload.password, user.password_hash)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # 4. Generate access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get("/me", response_model=UserSchema)
async def get_me(current_user: CurrentUser = Depends(get_current_user)) -> Any:
    """Fetch current user profile data."""
    return current_user

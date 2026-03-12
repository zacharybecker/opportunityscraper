import secrets
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    ldap_authenticate,
    local_authenticate,
    resolve_role,
)
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, RefreshRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Try local auth first
    user = await local_authenticate(body.username, body.password, db)

    if user:
        user.last_login = datetime.now(timezone.utc)
        await db.flush()
        access_token = create_access_token(str(user.id), user.role)
        refresh_token = create_refresh_token(str(user.id))
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )

    # Fall back to LDAP
    ldap_info = ldap_authenticate(body.username, body.password)
    if not ldap_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Find or create user
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    role = await resolve_role(ldap_info["groups"], db)

    if user:
        user.email = ldap_info["email"]
        user.display_name = ldap_info["display_name"]
        user.ldap_groups = ldap_info["groups"]
        user.role = role
        user.last_login = datetime.now(timezone.utc)
    else:
        user = User(
            username=body.username,
            email=ldap_info["email"],
            display_name=ldap_info["display_name"],
            role=role,
            ldap_groups=ldap_info["groups"],
            last_login=datetime.now(timezone.utc),
            is_superadmin=False,
            auth_provider="ldap",
        )
        db.add(user)

    await db.flush()

    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    display_name: str = ""


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if any users exist (first user bootstrap)
    user_count = (await db.execute(select(User.id).limit(1))).scalar_one_or_none()
    is_first_user = user_count is None

    role = "viewer"

    if is_first_user:
        role = "admin"

    # Check uniqueness
    existing = await db.execute(
        select(User).where(
            or_(User.username == body.username, User.email == body.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username or email already exists")

    user = User(
        username=body.username,
        email=body.email,
        display_name=body.display_name or body.username,
        role=role,
        auth_provider="local",
        password_hash=hash_password(body.password),
        email_verified=False,
        is_superadmin=is_first_user,
        last_login=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


class ForgotPasswordRequest(BaseModel):
    email: str


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == body.email, User.auth_provider == "local")
    )
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if not user:
        return {"status": "ok", "message": "If an account exists, a reset email will be sent"}

    token = secrets.token_urlsafe(32)
    user.password_reset_token = token
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    await db.flush()

    # Send email
    from app.notifications import send_email
    await send_email(
        user.email,
        "OpportunityScraper - Password Reset",
        f"""<h2>Password Reset</h2>
        <p>Use this token to reset your password:</p>
        <p><strong>{token}</strong></p>
        <p>Or click: <a href="/reset-password?token={token}">Reset Password</a></p>
        <p>This link expires in 1 hour.</p>""",
    )

    return {"status": "ok", "message": "If an account exists, a reset email will be sent"}


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(
            User.password_reset_token == body.token,
            User.password_reset_expires > datetime.now(timezone.utc),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.password_hash = hash_password(body.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await db.flush()

    return {"status": "ok", "message": "Password reset successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token(str(user.id), user.role)
    new_refresh = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)

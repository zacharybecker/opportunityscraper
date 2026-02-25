from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    ldap_authenticate,
    resolve_role,
)
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, RefreshRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
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

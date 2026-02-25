from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.config import settings
from app.db import get_db
from app.models import LdapGroupRole, User
from app.schemas import (
    AIConfigResponse,
    AIConfigUpdate,
    LdapGroupRoleCreate,
    LdapGroupRoleResponse,
    LdapGroupRoleUpdate,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ldap-groups", response_model=list[LdapGroupRoleResponse])
async def list_ldap_groups(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    result = await db.execute(select(LdapGroupRole))
    return [LdapGroupRoleResponse.model_validate(g) for g in result.scalars().all()]


@router.post("/ldap-groups", response_model=LdapGroupRoleResponse)
async def create_ldap_group(
    body: LdapGroupRoleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    group = LdapGroupRole(**body.model_dump())
    db.add(group)
    await db.flush()
    return LdapGroupRoleResponse.model_validate(group)


@router.put("/ldap-groups/{group_id}", response_model=LdapGroupRoleResponse)
async def update_ldap_group(
    group_id: str,
    body: LdapGroupRoleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    result = await db.execute(select(LdapGroupRole).where(LdapGroupRole.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(group, key, value)
    await db.flush()
    return LdapGroupRoleResponse.model_validate(group)


@router.delete("/ldap-groups/{group_id}")
async def delete_ldap_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    result = await db.execute(select(LdapGroupRole).where(LdapGroupRole.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    await db.delete(group)
    return {"status": "deleted"}


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    result = await db.execute(select(User).order_by(User.username))
    return [UserResponse.model_validate(u) for u in result.scalars().all()]


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(target, key, value)
    await db.flush()
    return UserResponse.model_validate(target)


@router.get("/ai-config", response_model=AIConfigResponse)
async def get_ai_config(user: User = Depends(require_role("admin"))):
    return AIConfigResponse(
        api_base_url=settings.AI_API_BASE_URL,
        model=settings.AI_MODEL,
        max_tokens=settings.AI_MAX_TOKENS,
        temperature=settings.AI_TEMPERATURE,
    )


@router.put("/ai-config", response_model=AIConfigResponse)
async def update_ai_config(
    body: AIConfigUpdate,
    user: User = Depends(require_role("admin")),
):
    if body.api_base_url is not None:
        settings.AI_API_BASE_URL = body.api_base_url
    if body.api_key is not None:
        settings.AI_API_KEY = body.api_key
    if body.model is not None:
        settings.AI_MODEL = body.model
    if body.max_tokens is not None:
        settings.AI_MAX_TOKENS = body.max_tokens
    if body.temperature is not None:
        settings.AI_TEMPERATURE = body.temperature

    return AIConfigResponse(
        api_base_url=settings.AI_API_BASE_URL,
        model=settings.AI_MODEL,
        max_tokens=settings.AI_MAX_TOKENS,
        temperature=settings.AI_TEMPERATURE,
    )


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    checks = {}

    # DB check
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # AI check
    checks["ai_configured"] = bool(settings.AI_API_KEY)
    checks["ai_endpoint"] = settings.AI_API_BASE_URL

    # LDAP check
    checks["ldap_configured"] = bool(settings.LDAP_SERVER_URI and settings.LDAP_BIND_DN)
    checks["auth_bypass"] = settings.AUTH_BYPASS

    return checks

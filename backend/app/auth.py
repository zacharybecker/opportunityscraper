import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models import LdapGroupRole, User

logger = logging.getLogger(__name__)
security = HTTPBearer()

ROLE_HIERARCHY = {"admin": 3, "analyst": 2, "viewer": 1}


def ldap_authenticate(username: str, password: str) -> Optional[dict]:
    """Authenticate via LDAP bind and return user info + groups."""
    if settings.AUTH_BYPASS:
        return {
            "username": username,
            "email": f"{username}@local",
            "display_name": username.title(),
            "groups": [],
        }
    try:
        import ldap

        conn = ldap.initialize(settings.LDAP_SERVER_URI)
        if settings.LDAP_USE_TLS:
            conn.start_tls_s()

        # First bind with service account to find user
        conn.simple_bind_s(settings.LDAP_BIND_DN, settings.LDAP_BIND_PASSWORD)

        search_filter = settings.LDAP_USER_SEARCH_FILTER.replace("{username}", username)
        result = conn.search_s(settings.LDAP_USER_SEARCH_BASE, ldap.SCOPE_SUBTREE, search_filter)

        if not result:
            return None

        user_dn, user_attrs = result[0]

        # Bind as user to verify password
        try:
            user_conn = ldap.initialize(settings.LDAP_SERVER_URI)
            if settings.LDAP_USE_TLS:
                user_conn.start_tls_s()
            user_conn.simple_bind_s(user_dn, password)
            user_conn.unbind_s()
        except ldap.INVALID_CREDENTIALS:
            return None

        # Get user groups
        group_filter = settings.LDAP_GROUP_SEARCH_FILTER.replace("{user_dn}", user_dn)
        groups = conn.search_s(settings.LDAP_GROUP_SEARCH_BASE, ldap.SCOPE_SUBTREE, group_filter)

        group_list = []
        for group_dn_str, group_attrs in groups:
            group_name = group_attrs.get("cn", [b""])[0]
            if isinstance(group_name, bytes):
                group_name = group_name.decode("utf-8")
            group_list.append({"dn": group_dn_str, "name": group_name})

        conn.unbind_s()

        email = user_attrs.get("mail", [b""])[0]
        display = user_attrs.get("displayName", [b""])[0]
        if isinstance(email, bytes):
            email = email.decode("utf-8")
        if isinstance(display, bytes):
            display = display.decode("utf-8")

        return {
            "username": username,
            "email": email,
            "display_name": display or username,
            "groups": group_list,
        }
    except Exception as e:
        logger.error(f"LDAP authentication error: {e}")
        return None


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_EXPIRE_MINUTES)
    payload = {"sub": user_id, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


async def resolve_role(groups: list[dict], db: AsyncSession) -> str:
    """Determine role from LDAP groups using ldap_group_roles table."""
    if not groups:
        return "viewer"

    group_dns = [g["dn"] for g in groups]
    result = await db.execute(
        select(LdapGroupRole).where(LdapGroupRole.group_dn.in_(group_dns))
    )
    mappings = result.scalars().all()

    if not mappings:
        return "viewer"

    best_role = "viewer"
    for mapping in mappings:
        if ROLE_HIERARCHY.get(mapping.role, 0) > ROLE_HIERARCHY.get(best_role, 0):
            best_role = mapping.role

    return best_role


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def require_role(min_role: str):
    """Dependency factory requiring a minimum role level."""
    def role_checker(user: User = Depends(get_current_user)):
        user_level = ROLE_HIERARCHY.get(user.role, 0)
        required_level = ROLE_HIERARCHY.get(min_role, 0)
        if user.is_superadmin:
            return user
        if user_level < required_level:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return role_checker

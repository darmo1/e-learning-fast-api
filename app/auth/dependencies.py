from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt

from app.auth.permissions import (
    Permission,
    is_admin_user,
    user_has_permission,
)
from app.users.services import get_user_by_email
from app.users.models import User, UserRole
from app.common.database import SessionDeep

import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


async def get_current_user(db: SessionDeep, token: str = Cookie(None, alias="access_token")):
    """Extrae y valida el usuario del JWT (cookie access_token)."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token provided in cookies",
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Solo tokens de acceso: rechaza refresh/activation tokens usados como access
        if payload.get("type") not in (None, "access"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    user = await get_user_by_email(db, email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user


async def get_current_user_optional(
    db: SessionDeep, token: str = Cookie(None, alias="access_token")
) -> User | None:
    """Como get_current_user pero devuelve None en vez de 401 sin sesión.

    Para endpoints públicos que igual quieren personalizar la respuesta si
    hay un usuario logueado (p. ej. el listado de feature flags)."""
    if not token:
        return None
    try:
        return await get_current_user(db, token)
    except HTTPException:
        return None


_is_admin = is_admin_user


def require_role(*roles: UserRole):
    """Dependencia que exige que el usuario autenticado tenga uno de los roles dados.

    Los admin/super_admin pasan siempre. Uso: Depends(require_role(UserRole.instructor))
    """

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if _is_admin(current_user):
            return current_user
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción",
            )
        return current_user

    return checker


def require_permission(permission: Permission):
    """Dependencia para endpoints del portal admin/CRM.

    - super_admin/admin: pasan siempre.
    - support: pasa si el permiso es base o le fue otorgado (tabla UserPermission).
    - resto: 403.
    """

    async def checker(
        db: SessionDeep, current_user: User = Depends(get_current_user)
    ) -> User:
        if user_has_permission(db, current_user, permission):
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción",
        )

    return checker

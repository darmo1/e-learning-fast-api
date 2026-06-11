from fastapi import Cookie, Depends, HTTPException, status
from jose import JWTError, jwt
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


def require_role(*roles: UserRole):
    """Dependencia que exige que el usuario autenticado tenga uno de los roles dados.

    Los admin pasan siempre. Uso: Depends(require_role(UserRole.instructor))
    """

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == UserRole.admin or current_user.is_admin:
            return current_user
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción",
            )
        return current_user

    return checker

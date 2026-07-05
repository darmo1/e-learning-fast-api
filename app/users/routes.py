from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.auth.dependencies import get_current_user, require_role
from app.auth.permissions import effective_permissions
from app.common.database import SessionDeep
from app.users.models import STAFF_ROLES, User, UserPermission
from app.users.schemas import UserOut
from app.users.services import get_user_by_email

user_router = APIRouter(prefix='/users', tags=['users'])

# Nota: el registro de usuarios vive en /auth/register (con email de activación).
# Se eliminó el POST /users/register duplicado que creaba cuentas sin activación.


@user_router.get("/info")
async def get_user_info(db: SessionDeep, current_user: User = Depends(get_current_user)):
    '''Endpoint para obtener la información del usuario autenticado'''
    user_data = current_user.model_dump(exclude={"password", "hashed_password"})

    # Permisos efectivos para que el FE gatee la UI del portal admin/CRM
    permissions: list[str] = []
    if current_user.role in STAFF_ROLES or current_user.is_admin:
        granted = set(
            db.exec(
                select(UserPermission.permission).where(
                    UserPermission.user_id == current_user.id
                )
            ).all()
        )
        permissions = sorted(effective_permissions(current_user, granted))

    return {**user_data, "permissions": permissions, "isLogged": True}


@user_router.get("/{email}", response_model=UserOut)
async def read_user(
    email: str,
    db: SessionDeep,
    current_user: User = Depends(require_role()),  # solo admin
):
    '''Endpoint para obtener un usuario por email (solo admin)'''
    db_user = await get_user_by_email(db, email)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

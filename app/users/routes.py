from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user, require_role
from app.common.database import SessionDeep
from app.users.models import User
from app.users.schemas import UserOut
from app.users.services import get_user_by_email

user_router = APIRouter(prefix='/users', tags=['users'])

# Nota: el registro de usuarios vive en /auth/register (con email de activación).
# Se eliminó el POST /users/register duplicado que creaba cuentas sin activación.


@user_router.get("/info")
async def get_user_info(db: SessionDeep, current_user: User = Depends(get_current_user)):
    '''Endpoint para obtener la información del usuario autenticado'''
    user_data = current_user.model_dump(exclude={"password", "hashed_password"})
    return {**user_data, "isLogged": True}


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

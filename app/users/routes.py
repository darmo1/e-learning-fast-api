from fastapi import APIRouter, Depends, HTTPException
from app.auth.dependencies import get_current_user
from app.common.database import SessionDeep, get_session 
from app.users.schemas import UserCreate, UserOut
from app.users.services import create_user, get_user_by_email


user_router = APIRouter(prefix='/users', tags=['users'])

@user_router.post("/register", response_model=UserOut)
async def register_user(user: UserCreate, db: SessionDeep):
    '''Endpoint para registrar un usuario'''
    db_user = await get_user_by_email(db, user.email)
   
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db, user)

@user_router.get("/info")
async def get_user_info(db: SessionDeep, token_data: dict = Depends(get_current_user)):
    '''Endpoint para obtener la información del usuario'''
 
    user_data = token_data.model_dump(exclude={"password", "hashed_password"})

    return { **user_data, "isLogged": True}
  


@user_router.get("/{email}", response_model=UserOut)
async def read_user(email: str, db: SessionDeep):
    '''Endpoint para obtener un usuario por email'''
    db_user = await get_user_by_email(db, email)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user



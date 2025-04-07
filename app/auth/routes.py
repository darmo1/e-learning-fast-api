from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import JSONResponse

# from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.auth.models import LoginRequest
from app.auth.services import verify_password, create_access_token, hash_password
from app.users.schemas import UserCreate, UserOut
from app.users.models import User
from app.users.services import get_user_by_email
from sqlmodel import Session, select
from app.common.database import SessionDeep
import os
from dotenv import load_dotenv
from app.auth.activation_service import send_activation_email

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 30))
DOMAIN = os.getenv("DOMAIN", "localhost")

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/login")
async def login(response: Response, form_data: LoginRequest, db: SessionDeep):
    """Endpoint para iniciar sesión y obtener un JWT."""
    user = await get_user_by_email(db, form_data.email)
    if not user or not verify_password(form_data.password, user.hashed_password):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Invalid credentials"},
        )
    # HTTPException(
    #         status_code=400, detail={"success": False, "message": "Invalid credentials"},
    #     )

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    response = JSONResponse(
        content={"success": True, "message": "Login exitoso"}
    )  # Creamos la respuesta JSON
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Debe ser True si usas HTTPS
        samesite="lax",
        domain=DOMAIN,
        path='/'
    )

    return response  # Retornamos la respuesta con la cookie


@auth_router.post("/register", response_model=UserOut)
def register(user_data: UserCreate, db: SessionDeep):
    # Verificar si el usuario ya existe
    statement = select(User).where(User.email == user_data.email)
    existing_user = db.exec(statement).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_password = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Create token activación
    token = create_access_token(data={"sub": user.id}, expires_delta=timedelta(hours=24))
     # Enviar correo con token de activación
    send_activation_email(user.email, token)

    return user

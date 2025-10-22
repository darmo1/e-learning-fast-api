from fastapi import APIRouter, Cookie, HTTPException, Depends, Response
from fastapi.responses import JSONResponse

# from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.auth.models import LoginRequest
from app.auth.services import (
    create_refresh_token,
    get_email_from_refresh_token,
    is_valid_refresh_token,
    verify_password,
    create_access_token,
    hash_password,
)
from app.auth.utils import is_dev
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
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", 7))
SECURE_COOKIE = not is_dev()
COOKIE_SAMESITE = "lax"

auth_router = APIRouter(prefix="/auth", tags=["auth"])


# --- Función Helper para establecer Cookies ---
def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str | None = None,  # Hacer refresh_token opcional
):
    """Establece las cookies de autenticación en la respuesta."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,  # ¡Esencial! No accesible por JS
        secure=SECURE_COOKIE,  # True en producción (HTTPS)
        samesite=COOKIE_SAMESITE,  # 'lax' recomendado
        path="/",  # Accesible en todo el sitio/API
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Tiempo de vida en segundos
        domain=DOMAIN,  # Omitir para localhost, especificar en prod si es necesario
    )
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,  # ¡Esencial!
            secure=SECURE_COOKIE,  # True en producción (HTTPS)
            samesite=COOKIE_SAMESITE,  # 'lax' recomendado
            # MUY IMPORTANTE: Limitar el path SOLO al endpoint de refresh
            path="/auth/refresh",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # Tiempo de vida largo
            domain=DOMAIN,  # Omitir para localhost, especificar en prod si es necesario
        )


# --- Función Helper para limpiar Cookies ---
def clear_auth_cookies(response: Response):
    """Limpia/elimina las cookies de autenticación."""
    response.delete_cookie(key="access_token", path="/", domain=DOMAIN)
    response.delete_cookie(
        key="refresh_token",
        path="/auth/refresh",  # Debe coincidir con el path usado al setear
        domain=DOMAIN,
    )


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

    refresh_token = create_refresh_token(
        data={"sub": user.email},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )

    response = JSONResponse(
        content={
            "success": True,
            "message": "Login exitoso",
            # "access_token": access_token,
            # "refresh_token": refresh_token,
        }
    )  # Creamos la respuesta JSON
    # response.set_cookie(
    #     key="access_token",
    #     value=access_token,
    #     httponly=True,
    #     secure=not is_dev(),  # Debe ser True si usas HTTPS
    #     samesite="none" if is_dev() else "none",
    #     # domain=DOMAIN,
    #     path="/",
    # )

    # response.set_cookie(
    #     key="refresh_token",
    #     value=refresh_token,
    #     httponly=True,
    #     secure=not is_dev(),  # Debe ser True si usas HTTPS
    #     samesite="none" if is_dev() else "none",
    #     # domain=DOMAIN,
    #     path="/",
    # )
    set_auth_cookies(response, access_token, refresh_token)

    return response  # Retornamos la respuesta con la cookie


@auth_router.post("/register", response_model=UserOut)
def register(user_data: UserCreate, db: SessionDeep):
    # Verificar si el usuario ya existe
    statement = select(User).where(User.email == user_data.email)
    existing_user = db.exec(statement).first()

    if existing_user:
        return JSONResponse(
            status_code=409,
            content={
                "error": "Usuario ya registrado",
                "message": "Usuario ya registrado",
            },
        )

    hashed_password = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Create token activación
    token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(hours=24)
    )
    # Enviar correo con token de activación
    send_activation_email(user.email, token)

    return user


@auth_router.post("/refresh")
async def refresh_token(
    response: Response,  # Inyecta Response para setear la nueva cookie
    db: SessionDeep,
    refresh_token: str | None = Cookie(None, alias="refresh_token"),
):

    if not refresh_token:
        # No necesitas limpiar cookies aquí, no había refresh token válido
        raise HTTPException(
            status_code=401, detail="Refresh token cookie no encontrada"
        )

    if not is_valid_refresh_token(refresh_token):
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Refresh token invalid or expired")

    try:
        email = get_email_from_refresh_token(refresh_token)
    except Exception:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await get_user_by_email(db, email)
    if not user:
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    response = JSONResponse(content={"access_token": new_access_token})
    # response.set_cookie(
    #     key="access_token",
    #     value=new_access_token,
    #     httponly=True,
    #     secure=not is_dev(),  # Debe ser True si usas HTTPS
    #     samesite="lax" if is_dev() else "none",
    #     path="/",
    # )
    set_auth_cookies(response, new_access_token, None)
    return response


@auth_router.post("/logout")
async def logout(response: Response):
    """Limpia/elimina las cookies de autenticación."""
    clear_auth_cookies(response)
    return JSONResponse(
        status_code=200, content={"success": True, "message": "Logout exitoso"}
    )

import logging
import os
from datetime import timedelta

from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlmodel import select

from app.auth.activation_service import send_activation_email, send_password_reset_email
from app.auth.models import ForgotPasswordRequest, LoginRequest, ResetPasswordRequest
from app.auth.services import (
    create_access_token,
    create_activation_token,
    create_password_reset_token,
    create_refresh_token,
    get_email_from_refresh_token,
    get_user_id_from_activation_token,
    get_user_id_from_reset_token,
    hash_password,
    is_valid_refresh_token,
    verify_password,
)
from app.auth.dependencies import get_current_user
from app.auth.utils import (
    forgot_password_rate_limiter,
    is_dev,
    login_rate_limiter,
    register_rate_limiter,
)
from app.common.database import SessionDeep
from app.users.models import User
from app.users.schemas import UserCreate, UserOut
from app.users.services import get_user_by_email

load_dotenv()
logger = logging.getLogger(__name__)

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", 7))
# Si se activa, el login exige cuenta verificada por email
REQUIRE_EMAIL_ACTIVATION = os.getenv("REQUIRE_EMAIL_ACTIVATION", "false").lower() == "true"

SECURE_COOKIE = not is_dev()
COOKIE_SAMESITE = "lax" if is_dev() else "none"
# Nota: ".vercel.app" está en la Public Suffix List, los navegadores rechazan
# cookies con ese Domain. Usar cookie host-only (None) salvo dominio propio.
DOMAIN_VALUE = os.getenv("COOKIE_DOMAIN") or None
REFRESH_COOKIE_PATH = "/api/v1/auth/refresh"

# Hash dummy para igualar el tiempo de respuesta cuando el email no existe
# (evita enumeración de usuarios por timing)
_DUMMY_HASH = hash_password("dummy-password-for-timing")

auth_router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str | None = None,
):
    """Establece las cookies de autenticación en la respuesta."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=SECURE_COOKIE,
        samesite=COOKIE_SAMESITE,
        path="/",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        domain=DOMAIN_VALUE,
    )
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=SECURE_COOKIE,
            samesite=COOKIE_SAMESITE,
            # Limitar el path SOLO al endpoint de refresh
            path=REFRESH_COOKIE_PATH,
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            domain=DOMAIN_VALUE,
        )


def clear_auth_cookies(response: Response):
    """Limpia/elimina las cookies de autenticación."""
    response.delete_cookie(key="access_token", path="/", domain=DOMAIN_VALUE)
    response.delete_cookie(
        key="refresh_token",
        path=REFRESH_COOKIE_PATH,
        domain=DOMAIN_VALUE,
    )


@auth_router.post("/login")
async def login(request: Request, form_data: LoginRequest, db: SessionDeep):
    """Endpoint para iniciar sesión y obtener un JWT."""
    login_rate_limiter.check(request)

    user = await get_user_by_email(db, form_data.email)
    if not user:
        # Verificación dummy para que la respuesta tarde lo mismo que con un
        # usuario real (anti enumeración por timing)
        verify_password(form_data.password, _DUMMY_HASH)
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Invalid credentials"},
        )

    if not verify_password(form_data.password, user.hashed_password):
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Invalid credentials"},
        )

    if REQUIRE_EMAIL_ACTIVATION and not user.is_active:
        return JSONResponse(
            status_code=403,
            content={"success": False, "message": "Cuenta no activada, revisa tu correo"},
        )

    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    refresh_token = create_refresh_token(
        data={"sub": user.email},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )

    # El FE (server action) setea las cookies con los tokens del body
    return JSONResponse(
        content={
            "success": True,
            "message": "Login exitoso",
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    )


@auth_router.post("/register", response_model=UserOut)
def register(request: Request, user_data: UserCreate, db: SessionDeep):
    register_rate_limiter.check(request)

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

    # Registro corporativo: valida la invitación ANTES de crear el usuario
    company = None
    if user_data.invite_token:
        from app.companies.services import validate_invite_for_registration

        company = validate_invite_for_registration(db, user_data.invite_token)

    hashed_password = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        is_active=False,
        company_id=company.id if company else None,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_activation_token(user.id)
    try:
        send_activation_email(user.email, token)
    except Exception:
        # El registro no debe fallar si el SMTP falla; el usuario puede pedir
        # reenvío más adelante
        logger.exception("No se pudo enviar el email de activación a %s", user.email)

    return user


@auth_router.get("/activate/{token}")
def activate_account(token: str, db: SessionDeep):
    """Activa la cuenta a partir del token enviado por email."""
    user_id = get_user_id_from_activation_token(token)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")

    if not user.is_active:
        user.is_active = True
        db.add(user)
        db.commit()

    return {"success": True, "message": "Cuenta activada"}


@auth_router.post("/resend-activation")
def resend_activation(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Reenvía el correo de activación al usuario autenticado.

    Permite completar la verificación a cuentas que se registraron pero nunca
    recibieron (o perdieron) el email original.
    """
    forgot_password_rate_limiter.check(request)

    if current_user.is_active:
        return {"success": True, "message": "La cuenta ya está activada"}

    token = create_activation_token(current_user.id)
    try:
        send_activation_email(current_user.email, token)
    except Exception:
        logger.exception(
            "No se pudo reenviar el email de activación a %s", current_user.email
        )
        raise HTTPException(
            status_code=502, detail="No se pudo enviar el correo, inténtalo más tarde"
        )

    return {"success": True, "message": "Te enviamos un nuevo correo de activación"}


@auth_router.get("/email-health")
def email_health():
    """Diagnóstico del proveedor de email (solo booleanos, sin exponer secretos)."""
    import requests as _requests

    api_key = os.getenv("BREVO_API_KEY")
    sender = (os.getenv("EMAIL_SENDER") or "").strip().lower()
    info: dict = {
        "provider": "brevo" if api_key else "gmail-smtp",
        "sender_configured": bool(sender),
    }

    if api_key:
        try:
            account = _requests.get(
                "https://api.brevo.com/v3/account",
                headers={"api-key": api_key},
                timeout=10,
            )
            info["brevo_key_valid"] = account.status_code == 200

            senders = _requests.get(
                "https://api.brevo.com/v3/senders",
                headers={"api-key": api_key},
                timeout=10,
            )
            if senders.status_code == 200:
                sender_list = senders.json().get("senders", [])
                info["sender_verified_in_brevo"] = any(
                    s.get("email", "").strip().lower() == sender and s.get("active")
                    for s in sender_list
                )
        except Exception:
            logger.exception("email-health: no se pudo consultar Brevo")
            info["brevo_reachable"] = False

    return info


@auth_router.post("/forgot-password")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: SessionDeep,
    background_tasks: BackgroundTasks,
):
    """Solicita el restablecimiento de contraseña.

    Siempre responde igual, exista o no la cuenta (anti enumeración). El email
    se envía en background para no filtrar la existencia por tiempo de respuesta.
    """
    forgot_password_rate_limiter.check(request)

    user = await get_user_by_email(db, body.email)
    if user:
        token = create_password_reset_token(user)

        def _send(email: str, reset_token: str):
            try:
                send_password_reset_email(email, reset_token)
            except Exception:
                logger.exception("No se pudo enviar el email de reset a %s", email)

        background_tasks.add_task(_send, user.email, token)

    return {
        "success": True,
        "message": "Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña",
    }


@auth_router.post("/reset-password")
async def reset_password(request: Request, body: ResetPasswordRequest, db: SessionDeep):
    """Restablece la contraseña con un token de un solo uso (30 min)."""
    login_rate_limiter.check(request)

    result = get_user_id_from_reset_token(body.token)
    if result is None:
        raise HTTPException(status_code=400, detail="Enlace inválido o expirado")

    user_id, fingerprint = result
    user = db.get(User, user_id)
    # El fingerprint ata el token al hash actual: si la contraseña ya cambió
    # (o el token ya se usó), deja de ser válido
    if not user or user.hashed_password[-12:] != fingerprint:
        raise HTTPException(status_code=400, detail="Enlace inválido o expirado")

    user.hashed_password = hash_password(body.new_password)
    db.add(user)
    db.commit()

    logger.info("Contraseña restablecida para el usuario %s", user.id)
    return {"success": True, "message": "Contraseña actualizada, ya puedes iniciar sesión"}


@auth_router.post("/refresh")
async def refresh_token(
    response: Response,
    db: SessionDeep,
    refresh_token: str | None = Cookie(None, alias="refresh_token"),
):
    if not refresh_token:
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
    set_auth_cookies(response, new_access_token, None)
    return response


@auth_router.post("/logout")
async def logout(response: Response):
    """Limpia/elimina las cookies de autenticación."""
    clear_auth_cookies(response)
    return JSONResponse(
        status_code=200, content={"success": True, "message": "Logout exitoso"}
    )

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY no está definido: la app no puede arrancar sin él")
ALGORITHM = os.getenv("JWT_ALGORITHM", 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_EXPIRE_DAYS", 7))



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Password hash
def hash_password(password:str) -> str:
    return pwd_context.hash(password)

# Verify password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Generate token JWT
def create_access_token( data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_password_reset_token(user, expires_delta: timedelta = timedelta(minutes=30)):
    """Token de reset de un solo uso: incluye una huella del hash actual de la
    contraseña, así deja de ser válido apenas la contraseña cambia."""
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": str(user.id),
        "exp": expire,
        "type": "password_reset",
        "fp": user.hashed_password[-12:],
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_user_id_from_reset_token(token: str) -> tuple[int, str] | None:
    """Devuelve (user_id, fingerprint) si el token de reset es válido."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return int(payload.get("sub")), payload.get("fp", "")
    except (JWTError, TypeError, ValueError):
        return None


def create_activation_token(user_id: int, expires_delta: timedelta = timedelta(hours=24)):
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": str(user_id), "exp": expire, "type": "activation"}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_user_id_from_activation_token(token: str) -> int | None:
    """Devuelve el user_id si el token de activación es válido, None si no."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "activation":
            return None
        return int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None

def create_refresh_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({
        "exp": expire,
        "type": "refresh"  # importante para validarlo después
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def is_valid_refresh_token(token: str) -> bool:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("type") == "refresh"
    except JWTError:
        return False

def get_email_from_refresh_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        return payload.get("sub")
    except (JWTError, ValueError):
        raise
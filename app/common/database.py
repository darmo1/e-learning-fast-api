from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy import text
from typing import Annotated
from fastapi import Depends, FastAPI
from dotenv import load_dotenv
load_dotenv()
import logging
import os

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está definido")

# echo solo en desarrollo: en producción loguea cada query (datos sensibles)
# pool_pre_ping: Neon (serverless) suspende y corta conexiones inactivas del
# pool; sin esto la primera request tras la pausa usa una conexión muerta -> 500
# check_same_thread: los tests usan SQLite y TestClient ejecuta la app en otro
# hilo; sin esto SQLite rechaza la conexión compartida
_connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("ENVIRONMENT", "development").lower() == "development",
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=_connect_args,
)

def _ensure_role_enum_values():
    """Agrega los roles nuevos (support, super_admin) al tipo enum de Postgres.

    El tipo `userrole` es un enum nativo; agregar miembros al Enum de Python
    no altera el tipo ya creado en la BD. Idempotente (IF NOT EXISTS) y
    requiere autocommit: ALTER TYPE ... ADD VALUE no funciona en transacción.
    """
    if engine.dialect.name != "postgresql":
        return
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_type WHERE typname = 'userrole'")
            ).first()
            if not exists:
                return
            for value in ("support", "super_admin"):
                conn.execute(
                    text(f"ALTER TYPE userrole ADD VALUE IF NOT EXISTS '{value}'")
                )
    except Exception:
        logger.exception("No se pudieron agregar los roles nuevos al enum userrole")


#Create tables
def create_all_tables(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    _ensure_role_enum_values()



async def get_session():
    ''' Usamos with para manejar las sesiones de la base de daots usando el contexto with para garantizar que la sesión se cierre correctamente cuando no se necesite'''
    with Session(engine) as session: 
        yield session

SessionDeep =  Annotated[Session, Depends(get_session)]
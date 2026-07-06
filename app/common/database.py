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
    """Crea tablas y migra el enum al arrancar.

    Los deploys levantan varios workers a la vez y todos ejecutan esto:
    sin serializar, create_all corre en paralelo y choca con
    "duplicate key ... pg_type_typname_nsp_index" (visto en prod 2026-07-06,
    tumbaba el worker y los requests fallaban durante el arranque). Un
    advisory lock de Postgres serializa el DDL entre workers/replicas.
    """
    if engine.dialect.name != "postgresql":
        SQLModel.metadata.create_all(engine)
        _ensure_role_enum_values()
        return

    _DDL_LOCK_KEY = 724488101
    lock_conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        lock_conn.execute(text(f"SELECT pg_advisory_lock({_DDL_LOCK_KEY})"))
        SQLModel.metadata.create_all(engine)
        _ensure_role_enum_values()
    except Exception:
        # Otro worker pudo haber creado los objetos primero; no tumbar el
        # arranque por eso (si la BD está caída, el healthcheck lo delata)
        logger.exception("create_all_tables falló; se continúa el arranque")
    finally:
        try:
            lock_conn.execute(text(f"SELECT pg_advisory_unlock({_DDL_LOCK_KEY})"))
        finally:
            lock_conn.close()



async def get_session():
    ''' Usamos with para manejar las sesiones de la base de daots usando el contexto with para garantizar que la sesión se cierre correctamente cuando no se necesite'''
    with Session(engine) as session: 
        yield session

SessionDeep =  Annotated[Session, Depends(get_session)]
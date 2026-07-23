import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, select

from app.auth.permissions import is_admin_user
from app.auth.utils import is_dev
from app.feature_flags.models import FeatureFlag, FeatureFlagEditor
from app.users.models import User
from app.users.services import get_user_by_email

logger = logging.getLogger(__name__)


def now_utc():
    return datetime.now(timezone.utc)


# Flags que la plataforma necesita que existan desde el arranque. El default
# depende del entorno: en desarrollo arrancan en el estado más conveniente
# para trabajar sin credenciales reales; en producción arrancan en el estado
# seguro (comportamiento real). Se seedean una sola vez — después el estado
# vive en la BD y lo controla el dashboard /flags.
_DEFAULT_FLAGS = [
    {
        "key": "ff-checkout-mercado-pago-sandbox",
        "description": (
            "Encendida: el checkout llama a Mercado Pago real. Apagada: "
            "simula un pago aprobado al instante (sin llamar a MP) e "
            "inscribe al usuario — para probar la compra completa sin "
            "credenciales de Mercado Pago."
        ),
        "enabled_dev": False,
        "enabled_prod": True,
    },
]


def seed_default_flags(db: Session) -> None:
    """Crea los flags conocidos si todavía no existen. Idempotente."""
    for spec in _DEFAULT_FLAGS:
        exists = db.exec(
            select(FeatureFlag).where(FeatureFlag.key == spec["key"])
        ).first()
        if exists:
            continue
        db.add(
            FeatureFlag(
                key=spec["key"],
                description=spec["description"],
                enabled=spec["enabled_dev"] if is_dev() else spec["enabled_prod"],
            )
        )
    db.commit()


def list_flags(db: Session) -> list[FeatureFlag]:
    return list(db.exec(select(FeatureFlag).order_by(FeatureFlag.key)).all())


def get_flag(db: Session, key: str) -> FeatureFlag | None:
    return db.exec(select(FeatureFlag).where(FeatureFlag.key == key)).first()


def is_enabled(db: Session, key: str, default: bool = False) -> bool:
    """Helper para que otros módulos (p. ej. payments) evalúen un flag sin
    acoplarse al resto de este módulo."""
    flag = get_flag(db, key)
    return flag.enabled if flag else default


def create_flag(db: Session, data) -> FeatureFlag:
    if get_flag(db, data.key):
        raise HTTPException(status_code=409, detail="Ya existe un flag con esa key")
    flag = FeatureFlag(key=data.key, description=data.description, enabled=data.enabled)
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag


def set_flag_enabled(db: Session, key: str, enabled: bool) -> FeatureFlag:
    flag = get_flag(db, key)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag no encontrado")
    flag.enabled = enabled
    flag.updated_at = now_utc()
    db.add(flag)
    db.commit()
    db.refresh(flag)
    return flag


def delete_flag(db: Session, key: str) -> None:
    flag = get_flag(db, key)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag no encontrado")
    db.delete(flag)
    db.commit()


def can_edit_flags(db: Session, user: User | None) -> bool:
    """admin/super_admin siempre; cualquier otro usuario si está en la lista
    de editores invitados."""
    if not user:
        return False
    if is_admin_user(user):
        return True
    granted = db.exec(
        select(FeatureFlagEditor).where(FeatureFlagEditor.user_id == user.id)
    ).first()
    return granted is not None


def list_editors(db: Session) -> list[dict]:
    rows = db.exec(select(FeatureFlagEditor)).all()
    out = []
    for row in rows:
        editor = db.get(User, row.user_id)
        granter = db.get(User, row.granted_by_id)
        if not editor:
            continue
        out.append(
            {
                "user_id": editor.id,
                "email": editor.email,
                "full_name": editor.full_name,
                "granted_by_email": granter.email if granter else "—",
                "created_at": row.created_at,
            }
        )
    return out


async def add_editor(db: Session, email: str, granted_by: User) -> dict:
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="No existe un usuario con ese email")
    existing = db.exec(
        select(FeatureFlagEditor).where(FeatureFlagEditor.user_id == user.id)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Ese usuario ya puede editar flags")
    db.add(FeatureFlagEditor(user_id=user.id, granted_by_id=granted_by.id))
    db.commit()
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "granted_by_email": granted_by.email,
        "created_at": now_utc(),
    }


def remove_editor(db: Session, user_id: int) -> None:
    row = db.exec(
        select(FeatureFlagEditor).where(FeatureFlagEditor.user_id == user_id)
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Ese usuario no es editor de flags")
    db.delete(row)
    db.commit()

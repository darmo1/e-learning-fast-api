from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user_optional, require_role
from app.auth.permissions import is_admin_user
from app.common.database import SessionDeep
from app.feature_flags import services
from app.feature_flags.dependencies import require_flag_editor
from app.feature_flags.schemas import (
    FeatureFlagCreate,
    FeatureFlagEditorCreate,
    FeatureFlagEditorOut,
    FeatureFlagListOut,
    FeatureFlagOut,
    FeatureFlagUpdate,
)
from app.users.models import User

feature_flags_router = APIRouter(prefix="/feature-flags", tags=["feature-flags"])


@feature_flags_router.get("/", response_model=FeatureFlagListOut)
def list_flags(
    db: SessionDeep,
    current_user: User | None = Depends(get_current_user_optional),
):
    """Listado público de flags (valores, no requiere sesión: los evalúa
    cualquier página, logueada o no). Incluye si el caller puede editarlos."""
    return {
        "flags": services.list_flags(db),
        "can_edit": services.can_edit_flags(db, current_user),
        "can_manage": current_user is not None and is_admin_user(current_user),
    }


@feature_flags_router.post("/", response_model=FeatureFlagOut, status_code=201)
def create_flag(
    body: FeatureFlagCreate,
    db: SessionDeep,
    _: User = Depends(require_role()),
):
    """Crear un flag nuevo. Solo admin/super_admin (crear la key es una
    decisión estructural, distinta de simplemente togglear un valor)."""
    return services.create_flag(db, body)


@feature_flags_router.patch("/{key}", response_model=FeatureFlagOut)
def toggle_flag(
    key: str,
    body: FeatureFlagUpdate,
    db: SessionDeep,
    _: User = Depends(require_flag_editor),
):
    """Prender/apagar un flag existente. admin/super_admin o editor invitado."""
    return services.set_flag_enabled(db, key, body.enabled)


@feature_flags_router.delete("/{key}", status_code=204)
def delete_flag(
    key: str,
    db: SessionDeep,
    _: User = Depends(require_role()),
):
    services.delete_flag(db, key)


@feature_flags_router.get("/editors", response_model=list[FeatureFlagEditorOut])
def list_editors(
    db: SessionDeep,
    _: User = Depends(require_role()),
):
    return services.list_editors(db)


@feature_flags_router.post("/editors", response_model=FeatureFlagEditorOut, status_code=201)
async def add_editor(
    body: FeatureFlagEditorCreate,
    db: SessionDeep,
    actor: User = Depends(require_role()),
):
    return await services.add_editor(db, body.email, actor)


@feature_flags_router.delete("/editors/{user_id}", status_code=204)
def remove_editor(
    user_id: int,
    db: SessionDeep,
    _: User = Depends(require_role()),
):
    services.remove_editor(db, user_id)

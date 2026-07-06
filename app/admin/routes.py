from fastapi import APIRouter, Depends, Query

from app.admin import services
from app.admin.schemas import (
    AdminOrderOut,
    AdminUserOut,
    PaginatedUsers,
    PermissionsOut,
    PermissionsUpdate,
    PlatformStats,
    UpdateUserRole,
    UpdateUserStatus,
)
from app.auth.dependencies import require_permission
from app.auth.permissions import Permission
from app.common.database import SessionDeep
from app.payments.models import OrderStatus
from app.users.models import User, UserRole

admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/stats", response_model=PlatformStats)
def platform_stats(
    db: SessionDeep,
    _: User = Depends(require_permission(Permission.stats_read)),
):
    """Métricas globales de la plataforma (dashboard del CRM)."""
    return services.get_platform_stats(db)


@admin_router.get("/users", response_model=PaginatedUsers)
def list_users(
    db: SessionDeep,
    search: str | None = Query(default=None, max_length=120),
    role: UserRole | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permission(Permission.users_read)),
):
    """Listado paginado de usuarios con búsqueda por email/nombre y filtro por rol."""
    users, total = services.list_users(db, search, role, page, page_size)
    return {"items": users, "total": total, "page": page, "page_size": page_size}


@admin_router.patch("/users/{user_id}/status", response_model=AdminUserOut)
def update_user_status(
    user_id: int,
    body: UpdateUserStatus,
    db: SessionDeep,
    actor: User = Depends(require_permission(Permission.users_write)),
):
    """Activa o desactiva una cuenta."""
    return services.set_user_status(db, actor, user_id, body.is_active)


@admin_router.patch("/users/{user_id}/role", response_model=AdminUserOut)
def update_user_role(
    user_id: int,
    body: UpdateUserRole,
    db: SessionDeep,
    actor: User = Depends(require_permission(Permission.roles_manage)),
):
    """Cambia el rol de un usuario (promover instructor, sumar soporte, etc.).

    Otorgar admin/super_admin requiere ser super_admin (validado en el service).
    """
    return services.set_user_role(db, actor, user_id, body.role)


@admin_router.get("/users/{user_id}/permissions", response_model=PermissionsOut)
def get_user_permissions(
    user_id: int,
    db: SessionDeep,
    _: User = Depends(require_permission(Permission.permissions_manage)),
):
    return services.get_user_permissions(db, user_id)


@admin_router.put("/users/{user_id}/permissions", response_model=PermissionsOut)
def set_user_permissions(
    user_id: int,
    body: PermissionsUpdate,
    db: SessionDeep,
    actor: User = Depends(require_permission(Permission.permissions_manage)),
):
    """Reemplaza el set de permisos extra de un usuario de soporte."""
    return services.set_user_permissions(db, actor, user_id, body.permissions)


@admin_router.get("/payouts")
def payouts(
    db: SessionDeep,
    _: User = Depends(require_permission(Permission.payments_read)),
):
    """Liquidaciones: neto por instructor sobre ventas aprobadas."""
    return services.get_payouts(db)


@admin_router.get("/orders")
def list_orders(
    db: SessionDeep,
    status: OrderStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permission(Permission.payments_read)),
):
    """Órdenes de compra con email del comprador y título del curso."""
    items, total = services.list_orders(db, status, page, page_size)
    return {
        "items": [AdminOrderOut(**item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

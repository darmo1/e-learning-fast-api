"""Catálogo de permisos del portal de administración (CRM).

Modelo de acceso:
- super_admin: todos los permisos, siempre. Único que puede gestionar roles
  de admin y tocar cuentas super_admin.
- admin: todos los permisos operativos; puede otorgar/revocar permisos extra
  a usuarios support (solo los de GRANTABLE_TO_SUPPORT).
- support: permisos base (SUPPORT_BASE_PERMISSIONS) + los extra otorgados.
- instructor/student: sin acceso al portal.
"""

from enum import Enum

from app.users.models import User, UserRole


class Permission(str, Enum):
    users_read = "users.read"            # ver listado y detalle de usuarios
    users_write = "users.write"          # activar/desactivar, reenviar activación
    roles_manage = "roles.manage"        # cambiar roles de usuarios
    permissions_manage = "permissions.manage"  # otorgar permisos a support
    companies_manage = "companies.manage"      # CRUD de empresas B2B
    payments_read = "payments.read"      # ver órdenes/pagos
    courses_moderate = "courses.moderate"  # moderar cursos/comentarios
    stats_read = "stats.read"            # dashboard de métricas


# Lo que un support puede hacer sin que le otorguen nada
SUPPORT_BASE_PERMISSIONS: frozenset[str] = frozenset(
    {Permission.users_read.value, Permission.stats_read.value}
)

# Lo máximo que un admin puede delegar en un support
GRANTABLE_TO_SUPPORT: frozenset[str] = frozenset(
    {
        Permission.users_write.value,
        Permission.companies_manage.value,
        Permission.payments_read.value,
        Permission.courses_moderate.value,
    }
)

ALL_PERMISSIONS: frozenset[str] = frozenset(p.value for p in Permission)


def is_admin_user(user: User) -> bool:
    """Admin o super_admin (incluye el flag legado is_admin)."""
    return user.role in (UserRole.admin, UserRole.super_admin) or user.is_admin


def user_has_permission(db, user: User, permission: Permission) -> bool:
    """Chequeo puntual de permiso (misma lógica que require_permission).

    admin/super_admin: siempre; support: base u otorgado; resto: nunca.
    """
    from sqlmodel import select

    from app.users.models import UserPermission

    if is_admin_user(user):
        return True
    if user.role != UserRole.support:
        return False
    if permission.value in SUPPORT_BASE_PERMISSIONS:
        return True
    granted = db.exec(
        select(UserPermission).where(
            UserPermission.user_id == user.id,
            UserPermission.permission == permission.value,
        )
    ).first()
    return granted is not None


def effective_permissions(user: User, granted: set[str] | None = None) -> set[str]:
    """Permisos efectivos de un usuario para mostrar/gatear en el FE.

    `granted` son las filas de UserPermission del usuario (solo aplica a support).
    """
    if user.role in (UserRole.super_admin, UserRole.admin) or user.is_admin:
        return set(ALL_PERMISSIONS)
    if user.role == UserRole.support:
        extra = {p for p in (granted or set()) if p in ALL_PERMISSIONS}
        return set(SUPPORT_BASE_PERMISSIONS) | extra
    return set()

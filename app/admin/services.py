from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.auth.permissions import (
    ALL_PERMISSIONS,
    GRANTABLE_TO_SUPPORT,
    SUPPORT_BASE_PERMISSIONS,
    effective_permissions,
)
from app.companies.models import Company
from app.courses.models import Course
from app.enrollments.models import Enrollment
from app.payments.models import Order, OrderStatus
from app.users.models import User, UserPermission, UserRole


def get_platform_stats(db: Session) -> dict:
    """Métricas globales para el dashboard del CRM."""
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)

    total_users = db.exec(select(func.count()).select_from(User)).one()
    by_role_rows = db.exec(
        select(User.role, func.count()).group_by(User.role)
    ).all()
    new_users = db.exec(
        select(func.count()).select_from(User).where(User.created_at >= month_ago)
    ).one()
    total_courses = db.exec(select(func.count()).select_from(Course)).one()
    total_enrollments = db.exec(select(func.count()).select_from(Enrollment)).one()
    enrollments_30d = db.exec(
        select(func.count())
        .select_from(Enrollment)
        .where(Enrollment.created_at >= month_ago)
    ).one()
    orders_approved = db.exec(
        select(func.count())
        .select_from(Order)
        .where(Order.status == OrderStatus.approved)
    ).one()
    revenue = db.exec(
        select(func.coalesce(func.sum(Order.amount), 0)).where(
            Order.status == OrderStatus.approved
        )
    ).one()
    total_companies = db.exec(select(func.count()).select_from(Company)).one()

    return {
        "total_users": total_users,
        "users_by_role": {str(role.value if hasattr(role, "value") else role): count for role, count in by_role_rows},
        "new_users_last_30d": new_users,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "enrollments_last_30d": enrollments_30d,
        "orders_approved": orders_approved,
        "revenue_approved": float(revenue),
        "total_companies": total_companies,
    }


def list_users(
    db: Session,
    search: str | None,
    role: UserRole | None,
    page: int,
    page_size: int,
) -> tuple[list[User], int]:
    query = select(User)
    count_query = select(func.count()).select_from(User)

    if search:
        pattern = f"%{search.strip().lower()}%"
        condition = func.lower(User.email).like(pattern) | func.lower(
            func.coalesce(User.full_name, "")
        ).like(pattern)
        query = query.where(condition)
        count_query = count_query.where(condition)

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    total = db.exec(count_query).one()
    users = db.exec(
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return users, total


def _get_target_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


def _guard_can_manage(actor: User, target: User):
    """Solo un super_admin puede tocar cuentas admin/super_admin."""
    if actor.id == target.id:
        raise HTTPException(
            status_code=400, detail="No puedes modificar tu propia cuenta desde aquí"
        )
    if (
        target.role in (UserRole.admin, UserRole.super_admin)
        and actor.role != UserRole.super_admin
    ):
        raise HTTPException(
            status_code=403,
            detail="Solo un super admin puede modificar cuentas de administración",
        )


def set_user_status(db: Session, actor: User, user_id: int, is_active: bool) -> User:
    target = _get_target_user(db, user_id)
    _guard_can_manage(actor, target)

    target.is_active = is_active
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


def set_user_role(db: Session, actor: User, user_id: int, new_role: UserRole) -> User:
    target = _get_target_user(db, user_id)
    _guard_can_manage(actor, target)

    # Otorgar admin o super_admin es exclusivo del super_admin
    if new_role in (UserRole.admin, UserRole.super_admin) and actor.role != UserRole.super_admin:
        raise HTTPException(
            status_code=403,
            detail="Solo un super admin puede otorgar roles de administración",
        )

    # Si deja de ser support, sus permisos extra ya no aplican
    if target.role == UserRole.support and new_role != UserRole.support:
        for row in db.exec(
            select(UserPermission).where(UserPermission.user_id == target.id)
        ).all():
            db.delete(row)

    target.role = new_role
    # Mantener coherente el flag legado is_admin con el rol
    target.is_admin = new_role in (UserRole.admin, UserRole.super_admin)
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


def get_user_permissions(db: Session, user_id: int) -> dict:
    target = _get_target_user(db, user_id)
    granted = set(
        db.exec(
            select(UserPermission.permission).where(UserPermission.user_id == user_id)
        ).all()
    )
    return {
        "user_id": target.id,
        "role": target.role,
        "base": sorted(SUPPORT_BASE_PERMISSIONS) if target.role == UserRole.support else [],
        "granted": sorted(granted),
        "effective": sorted(effective_permissions(target, granted)),
    }


def set_user_permissions(
    db: Session, actor: User, user_id: int, permissions: list[str]
) -> dict:
    target = _get_target_user(db, user_id)
    _guard_can_manage(actor, target)

    if target.role != UserRole.support:
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden otorgar permisos extra a usuarios de soporte",
        )

    requested = set(permissions)
    invalid = requested - ALL_PERMISSIONS
    if invalid:
        raise HTTPException(
            status_code=422, detail=f"Permisos desconocidos: {sorted(invalid)}"
        )

    # Un admin solo delega el subconjunto permitido; el super_admin no tiene tope
    if actor.role != UserRole.super_admin:
        not_grantable = requested - GRANTABLE_TO_SUPPORT
        if not_grantable:
            raise HTTPException(
                status_code=403,
                detail=f"Estos permisos no se pueden delegar a soporte: {sorted(not_grantable)}",
            )

    current = db.exec(
        select(UserPermission).where(UserPermission.user_id == user_id)
    ).all()
    current_values = {row.permission for row in current}

    for row in current:
        if row.permission not in requested:
            db.delete(row)
    for value in requested - current_values:
        db.add(UserPermission(user_id=user_id, permission=value, granted_by=actor.id))

    db.commit()
    return get_user_permissions(db, user_id)


def list_orders(
    db: Session, status: OrderStatus | None, page: int, page_size: int
) -> tuple[list[dict], int]:
    query = (
        select(Order, User.email, Course.title)
        .join(User, User.id == Order.user_id)
        .join(Course, Course.id == Order.course_id)
    )
    count_query = select(func.count()).select_from(Order)

    if status:
        query = query.where(Order.status == status)
        count_query = count_query.where(Order.status == status)

    total = db.exec(count_query).one()
    rows = db.exec(
        query.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = [
        {
            "id": order.id,
            "user_email": email,
            "course_title": title,
            "amount": order.amount,
            "currency": order.currency,
            "status": order.status.value,
            "payment_id": order.payment_id,
            "created_at": order.created_at,
        }
        for order, email, title in rows
    ]
    return items, total

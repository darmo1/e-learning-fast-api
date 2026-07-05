from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class UserRole(str, Enum):
    super_admin = "super_admin"
    admin = "admin"
    support = "support"
    instructor = "instructor"
    student = "student"


# Roles con acceso al portal de administración (CRM)
STAFF_ROLES = {UserRole.super_admin, UserRole.admin, UserRole.support}


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    hashed_password: str
    is_admin: bool = Field(default=False)
    is_active: bool = True
    role: UserRole = Field(default=UserRole.student)
    # Trabajadores corporativos: empresa a la que pertenecen (registro vía invite link)
    company_id: Optional[int] = Field(default=None, foreign_key="company.id", index=True)
    enrollments: List["Enrollment"] = Relationship(back_populates="user")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserPermission(SQLModel, table=True):
    """Permiso extra otorgado a un usuario de soporte por un admin.

    Los admin/super_admin tienen todos los permisos implícitos; esta tabla
    solo aplica a usuarios con rol support.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    permission: str = Field(max_length=64)
    granted_by: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActivationToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    token: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )  # 🔹 Genera un token único
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

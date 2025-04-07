from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class UserRole(str, Enum):
    admin = "admin"
    instructor = "instructor"
    student = "student"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    hashed_password: str
    is_admin: bool = Field(default=False)
    is_active: bool = True
    role: UserRole = Field(default=UserRole.student)
    enrollments: List["Enrollment"] = Relationship(back_populates="user")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ActivationToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    token: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )  # 🔹 Genera un token único
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

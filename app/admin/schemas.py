from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.users.models import UserRole


class PlatformStats(BaseModel):
    total_users: int
    users_by_role: dict[str, int]
    new_users_last_30d: int
    total_courses: int
    total_enrollments: int
    enrollments_last_30d: int
    orders_approved: int
    revenue_approved: float
    total_companies: int


class AdminUserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: UserRole
    is_active: bool
    company_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaginatedUsers(BaseModel):
    items: list[AdminUserOut]
    total: int
    page: int
    page_size: int


class UpdateUserStatus(BaseModel):
    is_active: bool


class UpdateUserRole(BaseModel):
    role: UserRole


class PermissionsUpdate(BaseModel):
    permissions: list[str] = Field(max_length=20)


class PermissionsOut(BaseModel):
    user_id: int
    role: UserRole
    base: list[str]
    granted: list[str]
    effective: list[str]


class AdminOrderOut(BaseModel):
    id: int
    user_email: str
    course_title: str
    amount: float
    currency: str
    status: str
    payment_id: Optional[str] = None
    created_at: datetime

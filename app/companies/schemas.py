from typing import Optional

from pydantic import Field
from sqlmodel import SQLModel


class CompanyCreate(SQLModel):
    name: str = Field(min_length=2, max_length=120)
    max_seats: int = Field(default=10, ge=0, le=10000)
    completion_goal_pct: float = Field(default=80.0, ge=0, le=100)


class CompanyUpdate(SQLModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    max_seats: Optional[int] = Field(default=None, ge=0, le=10000)
    completion_goal_pct: Optional[float] = Field(default=None, ge=0, le=100)
    is_active: Optional[bool] = None


class CompanyOut(SQLModel):
    id: int
    name: str
    is_active: bool
    max_seats: int
    seats_used: int
    completion_goal_pct: float
    invite_token: str


class CompanyCourseOut(SQLModel):
    course_id: int
    title: str
    enabled: bool


class InviteInfo(SQLModel):
    """Lo que ve públicamente quien abre el link de invitación."""

    company_name: str
    seats_available: bool
    courses: list[str]


class CourseStats(SQLModel):
    course_id: int
    course_title: str
    enrolled: int
    completed: int
    avg_progress_pct: float
    completion_pct: float
    goal_pct: float
    goal_met: Optional[bool]  # None cuando no hay inscritos aún


class CompanyStats(SQLModel):
    company_id: int
    company_name: str
    is_active: bool
    seats_used: int
    max_seats: int
    goal_pct: float
    courses: list[CourseStats]

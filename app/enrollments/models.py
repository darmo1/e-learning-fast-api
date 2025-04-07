from datetime import datetime
from sqlmodel import Column, DateTime, SQLModel, Field, Relationship, func
from typing import Optional


class Enrollment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    course_id: int = Field(foreign_key="course.id")
    user: "User" = Relationship(back_populates="enrollments")
    course: "Course" = Relationship(back_populates="enrollments")

    # BD asigna fecha/hora en la creación
    created_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    # BD asigna fecha/hora cuando hay un UPDATE
    updated_at: Optional[datetime] = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now()), default=None
    )
    deleted_at: Optional[datetime] = Field(default=None)

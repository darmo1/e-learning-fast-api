from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from app.enrollments.models import Enrollment

class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str
    price: float = Field(default=0) #significa que el curso es gratis
    category: str
    image_url: str
    instructor_id: int = Field(foreign_key="user.id")
    instructor: 'User' = Relationship()

    lessons: List['Lesson'] = Relationship(back_populates="course")
    enrollments: List['Enrollment'] = Relationship(back_populates="course")



# schemas.py
from typing import List
from pydantic import BaseModel

class CourseAnalyticsOut(BaseModel):
    course_id: int
    course_title: str
    category: str
    number_of_students: int
    # active_students: int
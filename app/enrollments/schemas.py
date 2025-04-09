from typing import Optional
from sqlmodel import SQLModel

class EnrollmentBase(SQLModel):
    course_id: int


class EnrollmentCreate(EnrollmentBase):
     user_id: Optional[int] = None

class EnrollmentResponse(EnrollmentBase):
    id: int

    class Config:
        from_attributes = True #Esta opción permite que los objetos SQLModel se puedan convertir a Pydantic models de manera sencilla
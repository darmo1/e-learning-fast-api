from sqlmodel import SQLModel
from typing import Optional


class CourseBase(SQLModel):

    title: str
    description: str
    price: float = 0
    category: str
    image_url: str
    instructor_id: Optional[int] = None


class CourseCreate(CourseBase):
    pass


class CourseResponse(CourseBase):
    id: int
    # Agregados de reseñas (None/0 si el curso aún no tiene)
    rating_avg: Optional[float] = None
    rating_count: int = 0

    class Config:
        from_attributes = True  # Esta opción permite que los objetos SQLModel se puedan convertir a Pydantic models de manera sencilla




class CourseEdit(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True
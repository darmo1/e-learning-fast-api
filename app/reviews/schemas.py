from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReviewUpsert(BaseModel):
    course_id: int
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = Field(default=None, max_length=2000)


class ReviewOut(BaseModel):
    id: int
    user_id: int
    user_name: str
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ReviewSummary(BaseModel):
    average: float
    count: int
    # Cantidad de reseñas por estrella: {"1": 0, ..., "5": 12}
    distribution: dict[str, int]


class CourseReviewsResponse(BaseModel):
    summary: ReviewSummary
    items: list[ReviewOut]
    # Reseña del usuario autenticado (para precargar el formulario), si existe
    my_review: Optional[ReviewOut] = None

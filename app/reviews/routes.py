from fastapi import APIRouter, Cookie, Depends, Query

from app.auth.dependencies import get_current_user
from app.common.database import SessionDeep
from app.reviews import services
from app.reviews.schemas import CourseReviewsResponse, ReviewOut, ReviewUpsert
from app.users.models import User

reviews_router = APIRouter(prefix="/reviews", tags=["reviews"])


@reviews_router.put("/", response_model=ReviewOut)
async def upsert_review(
    body: ReviewUpsert,
    db: SessionDeep,
    current_user: User = Depends(get_current_user),
):
    """Crea o actualiza (upsert) la reseña del usuario para un curso."""
    return services.upsert_review(db, current_user, body)


@reviews_router.get("/course/{course_id}", response_model=CourseReviewsResponse)
async def course_reviews(
    course_id: int,
    db: SessionDeep,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    access_token: str | None = Cookie(default=None),
):
    """Resumen + reseñas de un curso. Público; si hay sesión, incluye my_review."""
    current_user = None
    if access_token:
        try:
            current_user = await get_current_user(db, access_token)
        except Exception:
            current_user = None  # token inválido: se sirve como anónimo

    return services.get_course_reviews(db, course_id, limit, offset, current_user)


@reviews_router.delete("/{review_id}")
async def delete_review(
    review_id: int,
    db: SessionDeep,
    current_user: User = Depends(get_current_user),
):
    """Elimina una reseña (autor o staff con courses.moderate)."""
    services.delete_review(db, current_user, review_id)
    return {"success": True}

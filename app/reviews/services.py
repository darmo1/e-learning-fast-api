from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.auth.permissions import Permission, user_has_permission
from app.courses.models import Course
from app.enrollments.models import Enrollment
from app.reviews.models import CourseReview
from app.reviews.schemas import ReviewUpsert
from app.users.models import User


def _review_out(review: CourseReview, user_name: str | None) -> dict:
    return {
        "id": review.id,
        "user_id": review.user_id,
        "user_name": user_name or "Estudiante",
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
    }


def upsert_review(db: Session, user: User, data: ReviewUpsert) -> dict:
    """Crea o actualiza la reseña del usuario para un curso.

    Solo inscritos pueden reseñar; el instructor no puede reseñar su curso.
    """
    course = db.get(Course, data.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    if course.instructor_id == user.id:
        raise HTTPException(
            status_code=403, detail="No puedes reseñar tu propio curso"
        )

    enrolled = db.exec(
        select(Enrollment).where(
            Enrollment.user_id == user.id,
            Enrollment.course_id == data.course_id,
        )
    ).first()
    if not enrolled:
        raise HTTPException(
            status_code=403,
            detail="Debes estar inscrito en el curso para dejar una reseña",
        )

    review = db.exec(
        select(CourseReview).where(
            CourseReview.user_id == user.id,
            CourseReview.course_id == data.course_id,
        )
    ).first()

    if review:
        review.rating = data.rating
        review.comment = data.comment
        review.updated_at = datetime.now(timezone.utc)
    else:
        review = CourseReview(
            user_id=user.id,
            course_id=data.course_id,
            rating=data.rating,
            comment=data.comment,
        )

    db.add(review)
    db.commit()
    db.refresh(review)
    return _review_out(review, user.full_name)


def get_course_reviews(
    db: Session,
    course_id: int,
    limit: int = 20,
    offset: int = 0,
    current_user: User | None = None,
) -> dict:
    """Resumen + reseñas de un curso (público)."""
    if not db.get(Course, course_id):
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    rows = db.exec(
        select(CourseReview, User.full_name)
        .join(User, User.id == CourseReview.user_id)
        .where(CourseReview.course_id == course_id)
        .order_by(CourseReview.updated_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    distribution_rows = db.exec(
        select(CourseReview.rating, func.count())
        .where(CourseReview.course_id == course_id)
        .group_by(CourseReview.rating)
    ).all()
    distribution = {str(stars): 0 for stars in range(1, 6)}
    for rating, count in distribution_rows:
        distribution[str(rating)] = count

    count = sum(distribution.values())
    total_stars = sum(int(stars) * value for stars, value in distribution.items())
    average = round(total_stars / count, 1) if count else 0.0

    my_review = None
    if current_user:
        mine = db.exec(
            select(CourseReview).where(
                CourseReview.user_id == current_user.id,
                CourseReview.course_id == course_id,
            )
        ).first()
        if mine:
            my_review = _review_out(mine, current_user.full_name)

    return {
        "summary": {"average": average, "count": count, "distribution": distribution},
        "items": [_review_out(review, name) for review, name in rows],
        "my_review": my_review,
    }


def delete_review(db: Session, actor: User, review_id: int) -> None:
    """Borra una reseña: el autor o staff con courses.moderate."""
    review = db.get(CourseReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")

    if review.user_id != actor.id and not user_has_permission(
        db, actor, Permission.courses_moderate
    ):
        raise HTTPException(
            status_code=403, detail="No puedes eliminar esta reseña"
        )

    db.delete(review)
    db.commit()

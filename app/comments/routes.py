from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.auth.dependencies import get_current_user
from app.comments.schemas import CommentCreate, CommentResponse
from app.comments.services import add_comment, get_comments_by_lesson
from app.common.database import SessionDeep
from app.courses.models import Course
from app.enrollments.models import Enrollment
from app.lessons.models import Lesson
from app.users.models import STAFF_ROLES, User

comments_router = APIRouter(prefix="/comments", tags=["Comments"])


@comments_router.post("/", response_model=CommentResponse)
def create_comment(
    comment: CommentCreate,
    session: SessionDeep,
    current_user: User = Depends(get_current_user),
):
    """Comentar una lección: solo inscritos, el instructor dueño o staff."""
    lesson = session.get(Lesson, comment.lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lección no encontrada")

    course = session.get(Course, lesson.course_id)
    is_owner = course and course.instructor_id == current_user.id
    is_staff = current_user.role in STAFF_ROLES or current_user.is_admin

    if not is_owner and not is_staff:
        enrolled = session.exec(
            select(Enrollment).where(
                Enrollment.user_id == current_user.id,
                Enrollment.course_id == lesson.course_id,
            )
        ).first()
        if not enrolled:
            raise HTTPException(
                status_code=403,
                detail="Debes estar inscrito en el curso para comentar",
            )

    return add_comment(session, comment, user_id=current_user.id)


@comments_router.get("/lesson/{lesson_id}", response_model=list[CommentResponse])
def list_comments(lesson_id: int, session: SessionDeep):
    return get_comments_by_lesson(session, lesson_id)

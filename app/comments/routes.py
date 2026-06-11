from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.comments.schemas import CommentCreate, CommentResponse
from app.comments.services import add_comment, get_comments_by_lesson
from app.common.database import SessionDeep
from app.users.models import User

comments_router = APIRouter(prefix="/comments", tags=["Comments"])


@comments_router.post("/", response_model=CommentResponse)
def create_comment(
    comment: CommentCreate,
    session: SessionDeep,
    current_user: User = Depends(get_current_user),
):
    return add_comment(session, comment, user_id=current_user.id)


@comments_router.get("/lesson/{lesson_id}", response_model=list[CommentResponse])
def list_comments(lesson_id: int, session: SessionDeep):
    return get_comments_by_lesson(session, lesson_id)

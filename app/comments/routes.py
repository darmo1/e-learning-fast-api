from fastapi import APIRouter, HTTPException
from app.common.database import SessionDeep
from app.comments.schemas import CommentCreate, CommentResponse
from app.comments.services import add_comment, get_comments_by_lesson


comments_router = APIRouter(prefix="/comments", tags=["Comments"])

@comments_router.post("/", response_model=CommentResponse)
def create_comment(comment: CommentCreate, session: SessionDeep):
    return add_comment(session, comment)

@comments_router.get("/lesson/{lesson_id}", response_model=list[CommentResponse])
def list_comments(lesson_id: int, session:SessionDeep):
    comments = get_comments_by_lesson(session, lesson_id)
    if not comments:
        raise HTTPException(status_code=404, detail="No comments found for this lesson")
    return comments

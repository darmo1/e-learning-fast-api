from sqlmodel import select

from app.comments.models import Comment
from app.comments.schemas import CommentCreate
from app.common.database import SessionDeep


def add_comment(session: SessionDeep, comment_data: CommentCreate, user_id: int):
    new_comment = Comment(**comment_data.model_dump(), user_id=user_id)
    session.add(new_comment)
    session.commit()
    session.refresh(new_comment)
    return new_comment


def get_comments_by_lesson(session: SessionDeep, lesson_id: int):
    statement = select(Comment).where(Comment.lesson_id == lesson_id)
    return session.exec(statement).all()

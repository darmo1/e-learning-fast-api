from sqlmodel import SQLModel, Field, Relationship
from typing import Optional

class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    text: str
    lesson_id: int = Field(foreign_key="lesson.id")
    lesson: Optional["Lesson"] = Relationship(back_populates="comments")
    user_id: int = Field(foreign_key="user.id")
    user: Optional["User"] = Relationship()

'''
DELETE /comments/{id} → Eliminar un comentario.
PATCH /comments/{id} → Editar un comentario.
'''
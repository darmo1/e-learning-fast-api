from sqlmodel import Field, SQLModel


class CommentCreate(SQLModel):
    # user_id NO se acepta del cliente: se toma del token en la ruta
    text: str = Field(min_length=1, max_length=2000)
    lesson_id: int


class CommentResponse(SQLModel):
    id: int
    text: str
    user_id: int
    lesson_id: int

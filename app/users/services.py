from sqlmodel import select
from app.users.models import User
from app.users.schemas import UserCreate
from app.common.database import SessionDeep
from app.auth.services import hash_password


def create_user(db: SessionDeep, user: UserCreate):
    hashed_psw = hash_password(user.password)
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_psw,
        is_admin=False,
        is_active=False
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


async def get_user_by_email(db: SessionDeep, email: str):
    existing_user = db.exec(select(User).where(User.email == email)).first()
    return existing_user

"""Configuración de la suite: BD SQLite aislada + helpers de auth.

El env se fija ANTES de importar la app (el engine se crea al importar
app.common.database). Los tests no dependen de Postgres ni de docker.
"""

import os
from pathlib import Path

_TEST_DB = Path(__file__).parent / "test.db"
if _TEST_DB.exists():
    _TEST_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB}"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-ci"
os.environ["ENVIRONMENT"] = "production"  # sin echo SQL ni /docs

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.services import create_access_token, hash_password
from app.common.database import engine
from app.courses.models import Course
from app.lessons.models import Lesson
from app.main import app
from app.users.models import User, UserRole


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def db():
    with Session(engine) as session:
        yield session


def make_user(db: Session, email: str, role: UserRole = UserRole.student) -> User:
    from sqlmodel import select

    user = db.exec(select(User).where(User.email == email)).first()
    if not user:
        user = User(
            email=email,
            hashed_password=hash_password("Test!Passw0rd"),
            full_name=email.split("@")[0],
        )
    user.role = role
    user.is_admin = role in (UserRole.admin, UserRole.super_admin)
    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_cookies(email: str) -> dict:
    """Cookie de sesión válida sin pasar por /auth/login (evita rate limits)."""
    return {"access_token": create_access_token({"sub": email})}


def make_course(
    db: Session, instructor: User, title: str, price: float = 0, lessons: int = 0
) -> Course:
    course = Course(
        title=title,
        description=f"Descripción de {title}",
        price=price,
        category="Testing",
        image_url="",
        instructor_id=instructor.id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    for i in range(lessons):
        db.add(
            Lesson(
                title=f"{title} - Lección {i + 1}",
                description="",
                video_url="",
                is_free=False,
                course_id=course.id,
                position=i,
            )
        )
    if lessons:
        db.commit()
    return course

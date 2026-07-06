"""Reseñas: upsert con inscripción, resumen público y moderación."""

from app.enrollments.models import Enrollment
from app.users.models import UserRole

from tests.conftest import auth_cookies, make_course, make_user


def _setup(db):
    instructor = make_user(db, "rev-inst@test.local", UserRole.instructor)
    student = make_user(db, "rev-student@test.local")
    course = make_course(db, instructor, "Curso reseñable")
    db.add(Enrollment(user_id=student.id, course_id=course.id))
    db.commit()
    return instructor, student, course


def test_review_flow(client, db):
    instructor, student, course = _setup(db)
    cookies = auth_cookies(student.email)

    # Crear
    r = client.put(
        "/api/v1/reviews/",
        json={"course_id": course.id, "rating": 4, "comment": "Muy bueno"},
        cookies=cookies,
    )
    assert r.status_code == 200

    # Actualizar (upsert: sigue habiendo una sola reseña)
    r = client.put(
        "/api/v1/reviews/",
        json={"course_id": course.id, "rating": 5, "comment": "Excelente"},
        cookies=cookies,
    )
    assert r.status_code == 200

    data = client.get(f"/api/v1/reviews/course/{course.id}").json()
    assert data["summary"]["count"] == 1
    assert data["summary"]["average"] == 5.0

    # my_review presente con sesión
    data = client.get(f"/api/v1/reviews/course/{course.id}", cookies=cookies).json()
    assert data["my_review"]["rating"] == 5


def test_review_requires_enrollment(client, db):
    outsider = make_user(db, "rev-outsider@test.local")
    _, _, course = _setup(db)
    r = client.put(
        "/api/v1/reviews/",
        json={"course_id": course.id, "rating": 5},
        cookies=auth_cookies(outsider.email),
    )
    assert r.status_code == 403


def test_instructor_cannot_review_own_course(client, db):
    instructor, _, course = _setup(db)
    r = client.put(
        "/api/v1/reviews/",
        json={"course_id": course.id, "rating": 5},
        cookies=auth_cookies(instructor.email),
    )
    assert r.status_code == 403


def test_rating_out_of_range_is_422(client, db):
    _, student, course = _setup(db)
    r = client.put(
        "/api/v1/reviews/",
        json={"course_id": course.id, "rating": 9},
        cookies=auth_cookies(student.email),
    )
    assert r.status_code == 422


def test_delete_review_requires_author_or_moderator(client, db):
    _, student, course = _setup(db)
    client.put(
        "/api/v1/reviews/",
        json={"course_id": course.id, "rating": 3},
        cookies=auth_cookies(student.email),
    )
    review_id = client.get(f"/api/v1/reviews/course/{course.id}").json()["items"][0]["id"]

    support = make_user(db, "rev-support@test.local", UserRole.support)
    r = client.delete(f"/api/v1/reviews/{review_id}", cookies=auth_cookies(support.email))
    assert r.status_code == 403  # support sin courses.moderate

    admin = make_user(db, "rev-admin@test.local", UserRole.admin)
    r = client.delete(f"/api/v1/reviews/{review_id}", cookies=auth_cookies(admin.email))
    assert r.status_code == 200

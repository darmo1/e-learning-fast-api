"""Certificados: emisión al 100% de progreso y verificación pública."""

from sqlmodel import select

from app.enrollments.models import Enrollment
from app.lessons.models import Lesson
from app.users.models import UserRole

from tests.conftest import auth_cookies, make_course, make_user


def _setup(db, email_prefix: str, lessons: int = 2):
    instructor = make_user(db, f"{email_prefix}-inst@test.local", UserRole.instructor)
    student = make_user(db, f"{email_prefix}-student@test.local")
    course = make_course(db, instructor, f"Curso {email_prefix}", lessons=lessons)
    db.add(Enrollment(user_id=student.id, course_id=course.id))
    db.commit()
    lesson_ids = db.exec(select(Lesson.id).where(Lesson.course_id == course.id)).all()
    return student, course, list(lesson_ids)


def test_certificate_requires_full_completion(client, db):
    student, course, lesson_ids = _setup(db, "cert1")
    cookies = auth_cookies(student.email)

    # Sin completar nada: 409
    r = client.post(f"/api/v1/certificates/{course.id}", cookies=cookies)
    assert r.status_code == 409

    # Completar solo la primera lección: sigue en 409
    client.post(f"/api/v1/lessons/complete/{lesson_ids[0]}", cookies=cookies)
    r = client.post(f"/api/v1/certificates/{course.id}", cookies=cookies)
    assert r.status_code == 409

    # Completar todas: 200 con código
    for lesson_id in lesson_ids[1:]:
        client.post(f"/api/v1/lessons/complete/{lesson_id}", cookies=cookies)
    r = client.post(f"/api/v1/certificates/{course.id}", cookies=cookies)
    assert r.status_code == 200
    code = r.json()["code"]
    assert code

    # Idempotente: mismo código al reintentar
    r = client.post(f"/api/v1/certificates/{course.id}", cookies=cookies)
    assert r.status_code == 200
    assert r.json()["code"] == code

    # Verificación pública sin sesión
    r = client.get(f"/api/v1/certificates/verify/{code}")
    assert r.status_code == 200
    assert r.json()["course_title"] == course.title

    # Listado propio
    r = client.get("/api/v1/certificates/mine", cookies=cookies)
    assert r.status_code == 200
    assert any(cert["code"] == code for cert in r.json())


def test_certificate_requires_enrollment(client, db):
    _, course, _ = _setup(db, "cert2")
    outsider = make_user(db, "cert2-outsider@test.local")
    r = client.post(
        f"/api/v1/certificates/{course.id}", cookies=auth_cookies(outsider.email)
    )
    assert r.status_code == 403


def test_verify_unknown_code_is_404(client):
    # Código con formato válido pero inexistente
    unknown = "0" * 32
    assert client.get(f"/api/v1/certificates/verify/{unknown}").status_code == 404
    # Códigos malformados (muy cortos) los rechaza la validación
    assert client.get("/api/v1/certificates/verify/nope").status_code == 422

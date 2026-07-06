"""Catálogo público: búsqueda, categorías y agregados de rating."""

from app.users.models import UserRole

from tests.conftest import make_course, make_user


def test_search_and_category_filters(client, db):
    instructor = make_user(db, "catalog-inst@test.local", UserRole.instructor)
    make_course(db, instructor, "Python desde cero")
    make_course(db, instructor, "React avanzado")

    all_courses = client.get("/api/v1/course/all").json()
    assert len(all_courses) >= 2

    found = client.get("/api/v1/course/all?search=python").json()
    assert any("Python" in c["title"] for c in found)
    assert all("React" not in c["title"] for c in found)

    by_category = client.get("/api/v1/course/all?category=Testing").json()
    assert len(by_category) >= 2


def test_categories_endpoint(client, db):
    r = client.get("/api/v1/course/categories")
    assert r.status_code == 200
    assert "Testing" in r.json()


def test_catalog_includes_rating_fields(client):
    course = client.get("/api/v1/course/all").json()[0]
    assert "rating_avg" in course
    assert "rating_count" in course

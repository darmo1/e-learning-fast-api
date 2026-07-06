"""Ganancias del instructor y liquidaciones del CRM."""

from app.payments.models import Order, OrderStatus
from app.users.models import UserRole

from tests.conftest import auth_cookies, make_course, make_user


def test_earnings_and_payouts(client, db):
    instructor = make_user(db, "earn-inst@test.local", UserRole.instructor)
    buyer = make_user(db, "earn-buyer@test.local")
    admin = make_user(db, "earn-admin@test.local", UserRole.admin)
    course = make_course(db, instructor, "Curso vendible", price=50000)

    db.add(
        Order(
            user_id=buyer.id,
            course_id=course.id,
            amount=50000,
            currency="COP",
            status=OrderStatus.approved,
        )
    )
    # Las órdenes no aprobadas no cuentan
    db.add(
        Order(
            user_id=buyer.id,
            course_id=course.id,
            amount=99999,
            currency="COP",
            status=OrderStatus.pending,
        )
    )
    db.commit()

    r = client.get(
        "/api/v1/analytics/instructor/earnings", cookies=auth_cookies(instructor.email)
    )
    assert r.status_code == 200
    data = r.json()
    assert data["totals"]["sales"] == 1
    assert data["totals"]["gross"] == 50000.0
    assert data["totals"]["net"] == 50000.0 * (1 - data["platform_fee_pct"] / 100)

    r = client.get("/api/v1/admin/payouts", cookies=auth_cookies(admin.email))
    assert r.status_code == 200
    payouts = r.json()
    row = next(p for p in payouts["items"] if p["instructor_id"] == instructor.id)
    assert row["net"] == data["totals"]["net"]


def test_earnings_forbidden_for_students(client, db):
    student = make_user(db, "earn-student@test.local")
    r = client.get(
        "/api/v1/analytics/instructor/earnings", cookies=auth_cookies(student.email)
    )
    assert r.status_code == 403
    r = client.get("/api/v1/admin/payouts", cookies=auth_cookies(student.email))
    assert r.status_code == 403

"""Contrato de autorización del portal admin/CRM (RBAC de 5 roles)."""

from app.users.models import UserRole

from tests.conftest import auth_cookies, make_user


def test_student_cannot_access_admin(client, db):
    student = make_user(db, "rbac-student@test.local")
    r = client.get("/api/v1/admin/users", cookies=auth_cookies(student.email))
    assert r.status_code == 403


def test_anonymous_gets_401(client):
    assert client.get("/api/v1/admin/stats").status_code == 401


def test_support_has_base_read_permissions(client, db):
    support = make_user(db, "rbac-support@test.local", UserRole.support)
    cookies = auth_cookies(support.email)
    assert client.get("/api/v1/admin/users", cookies=cookies).status_code == 200
    assert client.get("/api/v1/admin/stats", cookies=cookies).status_code == 200


def test_support_needs_grant_for_writes(client, db):
    support = make_user(db, "rbac-support2@test.local", UserRole.support)
    admin = make_user(db, "rbac-admin@test.local", UserRole.admin)
    student = make_user(db, "rbac-student2@test.local")

    # Sin permiso: 403
    r = client.patch(
        f"/api/v1/admin/users/{student.id}/status",
        json={"is_active": False},
        cookies=auth_cookies(support.email),
    )
    assert r.status_code == 403

    # El admin delega users.write
    r = client.put(
        f"/api/v1/admin/users/{support.id}/permissions",
        json={"permissions": ["users.write"]},
        cookies=auth_cookies(admin.email),
    )
    assert r.status_code == 200
    assert "users.write" in r.json()["effective"]

    # Con permiso: 200
    r = client.patch(
        f"/api/v1/admin/users/{student.id}/status",
        json={"is_active": False},
        cookies=auth_cookies(support.email),
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_only_super_admin_grants_admin_roles(client, db):
    admin = make_user(db, "rbac-admin2@test.local", UserRole.admin)
    superadmin = make_user(db, "rbac-sa@test.local", UserRole.super_admin)
    student = make_user(db, "rbac-student3@test.local")

    r = client.patch(
        f"/api/v1/admin/users/{student.id}/role",
        json={"role": "admin"},
        cookies=auth_cookies(admin.email),
    )
    assert r.status_code == 403

    r = client.patch(
        f"/api/v1/admin/users/{student.id}/role",
        json={"role": "instructor"},
        cookies=auth_cookies(admin.email),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "instructor"

    r = client.patch(
        f"/api/v1/admin/users/{student.id}/role",
        json={"role": "admin"},
        cookies=auth_cookies(superadmin.email),
    )
    assert r.status_code == 200


def test_admin_cannot_delegate_outside_grantable_set(client, db):
    admin = make_user(db, "rbac-admin3@test.local", UserRole.admin)
    support = make_user(db, "rbac-support3@test.local", UserRole.support)

    r = client.put(
        f"/api/v1/admin/users/{support.id}/permissions",
        json={"permissions": ["roles.manage"]},
        cookies=auth_cookies(admin.email),
    )
    assert r.status_code == 403


def test_users_info_exposes_effective_permissions(client, db):
    support = make_user(db, "rbac-support4@test.local", UserRole.support)
    r = client.get("/api/v1/users/info", cookies=auth_cookies(support.email))
    assert r.status_code == 200
    assert "users.read" in r.json()["permissions"]


def test_email_health_is_admin_only(client):
    assert client.get("/api/v1/auth/email-health").status_code == 401

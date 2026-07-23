"""Smoke test del RBAC del CRM contra la BD local.

Uso: ENVIRONMENT=production venv/Scripts/python.exe -m scripts.smoke_admin
(ENVIRONMENT=production solo para silenciar el echo de SQL.)

Crea usuarios de prueba (super_admin, admin, support, student) y verifica los
contratos de autorización de /admin/*.
"""

import sys

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth.services import create_access_token, hash_password
from app.common.database import engine
from app.main import app
from app.users.models import User, UserPermission, UserRole

client = TestClient(app)

PASS = 0


def check(name: str, condition: bool, extra: str = ""):
    global PASS
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name} {extra}", file=sys.stderr)
    if condition:
        PASS += 1
    else:
        raise SystemExit(f"Smoke test falló en: {name} {extra}")


def make_user(db: Session, email: str, role: UserRole) -> User:
    user = db.exec(select(User).where(User.email == email)).first()
    if not user:
        user = User(
            email=email,
            hashed_password=hash_password("Sm0ke!Passw0rd"),
            full_name=email.split("@")[0],
        )
    user.role = role
    user.is_admin = role in (UserRole.admin, UserRole.super_admin)
    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def cookies(email: str) -> dict:
    return {"access_token": create_access_token({"sub": email})}


with Session(engine) as db:
    # NOTA: usar un dominio real (example.com) y no .local/.test — el
    # validador de email del endpoint /auth/login rechaza TLDs reservados
    # de uso especial, así que un email .local jamás podría iniciar sesión
    # por la UI aunque exista en la BD (solo estos checks, que inyectan la
    # cookie directamente, podían "loguearse").
    sa = make_user(db, "smoke-sa@example.com", UserRole.super_admin)
    adm = make_user(db, "smoke-admin@example.com", UserRole.admin)
    sup = make_user(db, "smoke-support@example.com", UserRole.support)
    stu = make_user(db, "smoke-student@example.com", UserRole.student)
    # Limpia permisos de corridas anteriores
    for row in db.exec(
        select(UserPermission).where(UserPermission.user_id == sup.id)
    ).all():
        db.delete(row)
    db.commit()
    sup_id, stu_id = sup.id, stu.id
    # Capturar como strings: fuera del with las instancias quedan detached
    sa_email, adm_email, sup_email, stu_email = (
        sa.email,
        adm.email,
        sup.email,
        stu.email,
    )

# 1. Un estudiante no entra al CRM
r = client.get("/api/v1/admin/users", cookies=cookies(stu_email))
check("student GET /admin/users -> 403", r.status_code == 403, str(r.status_code))

# 2. Sin sesión tampoco
r = client.get("/api/v1/admin/stats")
check("anon GET /admin/stats -> 401", r.status_code == 401, str(r.status_code))

# 3. Support: lectura base OK (users.read, stats.read)
r = client.get("/api/v1/admin/users", cookies=cookies(sup_email))
check("support GET /admin/users -> 200", r.status_code == 200, str(r.status_code))
r = client.get("/api/v1/admin/stats", cookies=cookies(sup_email))
check("support GET /admin/stats -> 200", r.status_code == 200, str(r.status_code))

# 4. Support sin users.write no puede desactivar cuentas
r = client.patch(
    f"/api/v1/admin/users/{stu_id}/status",
    json={"is_active": False},
    cookies=cookies(sup_email),
)
check("support PATCH status sin permiso -> 403", r.status_code == 403, str(r.status_code))

# 5. Admin le otorga users.write al support
r = client.put(
    f"/api/v1/admin/users/{sup_id}/permissions",
    json={"permissions": ["users.write"]},
    cookies=cookies(adm_email),
)
check("admin PUT permissions support -> 200", r.status_code == 200, str(r.status_code))
check(
    "permisos efectivos incluyen users.write",
    "users.write" in r.json()["effective"],
    str(r.json()["effective"]),
)

# 6. Ahora el support sí puede desactivar (y reactivar) al estudiante
r = client.patch(
    f"/api/v1/admin/users/{stu_id}/status",
    json={"is_active": False},
    cookies=cookies(sup_email),
)
check("support PATCH status con permiso -> 200", r.status_code == 200, str(r.status_code))
client.patch(
    f"/api/v1/admin/users/{stu_id}/status",
    json={"is_active": True},
    cookies=cookies(sup_email),
)

# 7. Admin no puede otorgar rol admin (solo super_admin)
r = client.patch(
    f"/api/v1/admin/users/{stu_id}/role",
    json={"role": "admin"},
    cookies=cookies(adm_email),
)
check("admin PATCH role=admin -> 403", r.status_code == 403, str(r.status_code))

# 8. Admin sí puede promover a instructor
r = client.patch(
    f"/api/v1/admin/users/{stu_id}/role",
    json={"role": "instructor"},
    cookies=cookies(adm_email),
)
check("admin PATCH role=instructor -> 200", r.status_code == 200, str(r.status_code))

# 9. Super admin puede otorgar admin (y revertir)
r = client.patch(
    f"/api/v1/admin/users/{stu_id}/role",
    json={"role": "admin"},
    cookies=cookies(sa_email),
)
check("super_admin PATCH role=admin -> 200", r.status_code == 200, str(r.status_code))
client.patch(
    f"/api/v1/admin/users/{stu_id}/role",
    json={"role": "student"},
    cookies=cookies(sa_email),
)

# 10. Admin no puede delegar un permiso fuera del set otorgable
r = client.put(
    f"/api/v1/admin/users/{sup_id}/permissions",
    json={"permissions": ["roles.manage"]},
    cookies=cookies(adm_email),
)
check("admin delega roles.manage -> 403", r.status_code == 403, str(r.status_code))

# 11. /users/info expone los permisos efectivos del support
r = client.get("/api/v1/users/info", cookies=cookies(sup_email))
perms = r.json().get("permissions", [])
check(
    "/users/info del support trae permisos",
    r.status_code == 200 and "users.read" in perms and "users.write" in perms,
    str(perms),
)

# 12. email-health ya no es público
r = client.get("/api/v1/auth/email-health")
check("anon GET /auth/email-health -> 401", r.status_code == 401, str(r.status_code))

# 13. El checkout muerto de Stripe ya no existe
r = client.post("/api/v1/checkout/webhook")
check("POST /checkout/webhook -> 404", r.status_code == 404, str(r.status_code))

print(f"\nSmoke test OK: {PASS} checks", file=sys.stderr)

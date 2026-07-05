"""Promueve un usuario existente a super_admin (bootstrap del CRM).

Uso (desde la raíz del BE, con el venv activo y DATABASE_URL apuntando a la BD):
    python -m scripts.promote_super_admin correo@ejemplo.com

Es la única vía prevista para crear el primer super_admin; después, los roles
se gestionan desde el CRM (/admin/users/{id}/role).
"""

import sys

from sqlmodel import Session, select

from app.common.database import engine
from app.users.models import User, UserRole


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python -m scripts.promote_super_admin <email>")
        return 1

    email = sys.argv[1].strip().lower()
    with Session(engine) as db:
        user = db.exec(select(User).where(User.email == email)).first()
        if not user:
            print(f"No existe un usuario con email {email}")
            return 1

        user.role = UserRole.super_admin
        user.is_admin = True
        user.is_active = True
        db.add(user)
        db.commit()
        print(f"{email} ahora es super_admin (id={user.id})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import csv
import io
import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlmodel import Session, func, select

from app.companies.models import Company, CompanyCourse, new_invite_token
from app.companies.schemas import (
    CompanyCreate,
    CompanyStats,
    CompanyUpdate,
    CourseStats,
    InviteInfo,
)
from app.courses.models import Course
from app.enrollments.models import Enrollment
from app.lessons.models import Lesson, LessonProgress
from app.users.models import User

logger = logging.getLogger(__name__)


def seats_used(db: Session, company_id: int) -> int:
    return db.exec(
        select(func.count()).select_from(User).where(User.company_id == company_id)
    ).one()


def create_company(db: Session, data: CompanyCreate) -> Company:
    company = Company(**data.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    logger.info("Empresa creada: %s (id=%s, cupos=%s)", company.name, company.id, company.max_seats)
    return company


def list_companies(db: Session) -> list[dict]:
    companies = db.exec(select(Company).order_by(Company.created_at.desc())).all()
    return [
        {**c.model_dump(), "seats_used": seats_used(db, c.id)} for c in companies
    ]


def get_company(db: Session, company_id: int) -> Company:
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company


def update_company(db: Session, company_id: int, data: CompanyUpdate) -> Company:
    company = get_company(db, company_id)
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(company, key, value)
    company.updated_at = datetime.now(timezone.utc)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def regenerate_invite_token(db: Session, company_id: int) -> Company:
    """Revoca el link anterior generando un token nuevo."""
    company = get_company(db, company_id)
    company.invite_token = new_invite_token()
    company.updated_at = datetime.now(timezone.utc)
    db.add(company)
    db.commit()
    db.refresh(company)
    logger.info("Invite token regenerado para empresa %s", company_id)
    return company


def set_course_enabled(db: Session, company_id: int, course_id: int, enabled: bool):
    get_company(db, company_id)
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    link = db.exec(
        select(CompanyCourse).where(
            CompanyCourse.company_id == company_id,
            CompanyCourse.course_id == course_id,
        )
    ).first()

    if enabled and not link:
        db.add(CompanyCourse(company_id=company_id, course_id=course_id))
        db.commit()
    elif not enabled and link:
        db.delete(link)
        db.commit()

    return {"course_id": course_id, "enabled": enabled}


def list_company_courses(db: Session, company_id: int) -> list[dict]:
    """Todos los cursos de la plataforma con su flag de habilitado para la empresa."""
    get_company(db, company_id)
    enabled_ids = set(
        db.exec(
            select(CompanyCourse.course_id).where(CompanyCourse.company_id == company_id)
        ).all()
    )
    courses = db.exec(select(Course)).all()
    return [
        {"course_id": c.id, "title": c.title, "enabled": c.id in enabled_ids}
        for c in courses
    ]


# ---------- Invitación / registro corporativo ----------

def get_company_by_invite_token(db: Session, token: str) -> Company | None:
    return db.exec(select(Company).where(Company.invite_token == token)).first()


def get_invite_info(db: Session, token: str) -> InviteInfo:
    """Info pública del link de invitación. No revela cupos exactos ni IDs."""
    company = get_company_by_invite_token(db, token)
    if not company or not company.is_active:
        raise HTTPException(status_code=404, detail="Invitación no válida")

    titles = db.exec(
        select(Course.title)
        .join(CompanyCourse, CompanyCourse.course_id == Course.id)
        .where(CompanyCourse.company_id == company.id)
    ).all()

    return InviteInfo(
        company_name=company.name,
        seats_available=seats_used(db, company.id) < company.max_seats,
        courses=list(titles),
    )


def validate_invite_for_registration(db: Session, token: str) -> Company:
    """Valida el token al registrarse: empresa activa y con cupos libres."""
    company = get_company_by_invite_token(db, token)
    if not company or not company.is_active:
        raise HTTPException(status_code=400, detail="Invitación no válida")
    if seats_used(db, company.id) >= company.max_seats:
        raise HTTPException(status_code=409, detail="La empresa no tiene cupos disponibles")
    return company


def company_has_course(db: Session, company_id: int, course_id: int) -> bool:
    link = db.exec(
        select(CompanyCourse).where(
            CompanyCourse.company_id == company_id,
            CompanyCourse.course_id == course_id,
        )
    ).first()
    return link is not None


def user_has_company_access(db: Session, user: User, course_id: int) -> bool:
    """True si el usuario pertenece a una empresa activa con el curso habilitado."""
    if not user.company_id:
        return False
    company = db.get(Company, user.company_id)
    if not company or not company.is_active:
        return False
    return company_has_course(db, company.id, course_id)


# ---------- Estadísticas e informes ----------

def get_company_stats(db: Session, company_id: int) -> CompanyStats:
    company = get_company(db, company_id)

    enabled_courses = db.exec(
        select(Course)
        .join(CompanyCourse, CompanyCourse.course_id == Course.id)
        .where(CompanyCourse.company_id == company_id)
    ).all()

    course_stats: list[CourseStats] = []
    for course in enabled_courses:
        lesson_ids = db.exec(
            select(Lesson.id).where(Lesson.course_id == course.id)
        ).all()
        total_lessons = len(lesson_ids)

        # Trabajadores de la empresa inscritos en el curso
        enrolled_user_ids = db.exec(
            select(Enrollment.user_id)
            .join(User, User.id == Enrollment.user_id)
            .where(
                Enrollment.course_id == course.id,
                User.company_id == company_id,
            )
        ).all()
        enrolled = len(enrolled_user_ids)

        completed = 0
        progress_sum = 0.0
        if enrolled and total_lessons:
            for uid in enrolled_user_ids:
                done = db.exec(
                    select(func.count())
                    .select_from(LessonProgress)
                    .where(
                        LessonProgress.user_id == uid,
                        LessonProgress.lesson_id.in_(lesson_ids),
                    )
                ).one()
                progress_sum += done / total_lessons
                if done == total_lessons:
                    completed += 1

        avg_progress_pct = round((progress_sum / enrolled) * 100, 1) if enrolled else 0.0
        completion_pct = round((completed / enrolled) * 100, 1) if enrolled else 0.0
        goal_met = completion_pct >= company.completion_goal_pct if enrolled else None

        course_stats.append(
            CourseStats(
                course_id=course.id,
                course_title=course.title,
                enrolled=enrolled,
                completed=completed,
                avg_progress_pct=avg_progress_pct,
                completion_pct=completion_pct,
                goal_pct=company.completion_goal_pct,
                goal_met=goal_met,
            )
        )

    return CompanyStats(
        company_id=company.id,
        company_name=company.name,
        is_active=company.is_active,
        seats_used=seats_used(db, company_id),
        max_seats=company.max_seats,
        goal_pct=company.completion_goal_pct,
        courses=course_stats,
    )


def build_company_report_csv(db: Session, company_id: int) -> str:
    """Informe CSV por curso para enviar a la empresa."""
    stats = get_company_stats(db, company_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Empresa", stats.company_name])
    writer.writerow(["Cupos usados", f"{stats.seats_used}/{stats.max_seats}"])
    writer.writerow(["Meta de finalización (%)", stats.goal_pct])
    writer.writerow([])
    writer.writerow(
        ["Curso", "Inscritos", "Completados", "% Avance promedio", "% Finalización", "Meta cumplida"]
    )
    for c in stats.courses:
        goal_label = "Sin inscritos" if c.goal_met is None else ("Sí" if c.goal_met else "No")
        writer.writerow(
            [c.course_title, c.enrolled, c.completed, c.avg_progress_pct, c.completion_pct, goal_label]
        )
    return buffer.getvalue()

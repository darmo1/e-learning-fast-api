from fastapi import APIRouter, Depends, Response
from sqlmodel import Session

from app.auth.dependencies import require_permission
from app.auth.permissions import Permission
from app.common.database import SessionDeep
from app.companies import services
from app.companies.schemas import (
    CompanyCreate,
    CompanyCourseOut,
    CompanyOut,
    CompanyStats,
    CompanyUpdate,
    InviteInfo,
)
from app.users.models import User

companies_router = APIRouter(prefix="/companies", tags=["companies"])

# Admin/super_admin siempre; support solo si le otorgaron companies.manage
AdminUser = Depends(require_permission(Permission.companies_manage))


# ---------- Público: link de invitación ----------

@companies_router.get("/invite/{token}", response_model=InviteInfo)
def invite_info(token: str, db: SessionDeep):
    """Info pública que ve el trabajador al abrir el link de invitación."""
    return services.get_invite_info(db, token)


# ---------- Admin ----------

@companies_router.post("/", response_model=CompanyOut)
def create_company(data: CompanyCreate, db: SessionDeep, _: User = AdminUser):
    company = services.create_company(db, data)
    return {**company.model_dump(), "seats_used": 0}


@companies_router.get("/", response_model=list[CompanyOut])
def list_companies(db: SessionDeep, _: User = AdminUser):
    return services.list_companies(db)


@companies_router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, db: SessionDeep, _: User = AdminUser):
    company = services.get_company(db, company_id)
    return {**company.model_dump(), "seats_used": services.seats_used(db, company_id)}


@companies_router.patch("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int, data: CompanyUpdate, db: SessionDeep, _: User = AdminUser
):
    company = services.update_company(db, company_id, data)
    return {**company.model_dump(), "seats_used": services.seats_used(db, company_id)}


@companies_router.post("/{company_id}/regenerate-token", response_model=CompanyOut)
def regenerate_token(company_id: int, db: SessionDeep, _: User = AdminUser):
    company = services.regenerate_invite_token(db, company_id)
    return {**company.model_dump(), "seats_used": services.seats_used(db, company_id)}


@companies_router.get("/{company_id}/courses", response_model=list[CompanyCourseOut])
def company_courses(company_id: int, db: SessionDeep, _: User = AdminUser):
    """Todos los cursos con su flag de habilitado para esta empresa."""
    return services.list_company_courses(db, company_id)


@companies_router.put("/{company_id}/courses/{course_id}")
def enable_course(company_id: int, course_id: int, db: SessionDeep, _: User = AdminUser):
    return services.set_course_enabled(db, company_id, course_id, enabled=True)


@companies_router.delete("/{company_id}/courses/{course_id}")
def disable_course(company_id: int, course_id: int, db: SessionDeep, _: User = AdminUser):
    return services.set_course_enabled(db, company_id, course_id, enabled=False)


@companies_router.get("/{company_id}/stats", response_model=CompanyStats)
def company_stats(company_id: int, db: SessionDeep, _: User = AdminUser):
    return services.get_company_stats(db, company_id)


@companies_router.get("/{company_id}/report")
def company_report(company_id: int, db: SessionDeep, _: User = AdminUser):
    """Informe CSV descargable con los objetivos por curso."""
    csv_content = services.build_company_report_csv(db, company_id)
    company = services.get_company(db, company_id)
    filename = f"informe-{company.name.lower().replace(' ', '-')}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import get_current_user, require_role
from app.common.database import SessionDeep
from app.courses import services
from app.courses.schemas import CourseBase, CourseEdit, CourseResponse
from app.users.models import User, UserRole

course_router = APIRouter(prefix="/course", tags=["courses"])


@course_router.post("/create", response_model=CourseResponse)
async def create_course(
    course: CourseBase,
    db: SessionDeep,
    current_user: User = Depends(require_role(UserRole.instructor)),
):
    """Endpoint para crear un curso (solo instructores/admin)"""
    course_dict = course.model_dump()
    course_dict["instructor_id"] = current_user.id

    return services.create_course(db, course_dict)


@course_router.patch("/update/{course_id}")
async def update_course(
    course_id: int,
    update_data: CourseEdit,
    db: SessionDeep,
    current_user: User = Depends(require_role(UserRole.instructor)),
):
    """Actualizar curso (solo el instructor dueño; valida ownership en el service)"""
    course_dict = update_data.model_dump(exclude_unset=True)
    return services.update_course(db, course_id, course_dict, current_user)


@course_router.get("/")
async def get_courses_by_user(
    db: SessionDeep,
    current_user: User = Depends(get_current_user),
    search: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=80),
):
    """Catálogo para usuarios logueados: excluye los cursos ya inscritos."""
    return services.get_courses(db, current_user.id, search, category)


@course_router.get("/all", response_model=list[CourseResponse])
async def get_all_courses(
    db: SessionDeep,
    search: str | None = Query(default=None, max_length=120),
    category: str | None = Query(default=None, max_length=80),
):
    """Catálogo público con búsqueda por texto y filtro por categoría"""
    return services.get_all_courses(db, search, category)


@course_router.get("/categories", response_model=list[str])
async def get_categories(db: SessionDeep):
    """Categorías con cursos publicados (para los filtros del catálogo).

    Nota: debe declararse antes de /{course_id} para que "categories" no se
    intente parsear como id.
    """
    return services.get_categories(db)


@course_router.get("/instructor")
async def get_courses_by_instructor(
    db: SessionDeep,
    current_user: User = Depends(require_role(UserRole.instructor)),
):
    return services.get_courses_by_instructor(db, current_user.id)


@course_router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: SessionDeep):
    """Endpoint para obtener un curso por id"""
    course = services.get_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

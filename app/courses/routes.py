from fastapi import APIRouter, HTTPException, Depends
from app.common.database import SessionDeep, get_session
from app.courses.schemas import CourseCreate, CourseEdit, CourseResponse, CourseBase
from app.courses import services
from app.auth.dependencies import get_current_user

course_router = APIRouter(prefix="/course", tags=["courses"])


@course_router.post("/create", response_model=CourseResponse)
async def create_course(
    course: CourseBase, db: SessionDeep, token_data: dict = Depends(get_current_user)
):
    """Endpoint para crear un curso"""

    # Convertir a diccionario antes de desestructurar
    course_dict = course.model_dump()
    course_dict["instructor_id"] = token_data.id

    return services.create_course(db, course_dict)


@course_router.patch("/update/{course_id}")
async def update_course(
    course_id: int,
    update_data: CourseEdit,
    db: SessionDeep,
    token_data: dict = Depends(get_current_user),
):
    """Actualizar curso (solo los campos modificados)"""
    course_dict = update_data.model_dump(exclude_unset=True)
    return services.update_course(db, course_id, course_dict, token_data)


@course_router.get("/")
async def get_courses_by_user(
    db: SessionDeep, token_data: dict = Depends(get_current_user)
):
    user_id = token_data.id
    return services.get_courses(db, user_id)


@course_router.get("/all", response_model=list[CourseResponse])
async def get_all_courses(db: SessionDeep):
    """Endpoint para obtener todos los cursos"""
    return services.get_all_courses(db)


@course_router.get("/instructor")
async def get_courses_by_instructor(
    db: SessionDeep, token_data: dict = Depends(get_current_user)
):
    user_id = token_data.id
    user_role = token_data.role.value

    if user_role is not "instructor":
        pass

    return services.get_courses_by_instructor(db, user_id)


@course_router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: SessionDeep):
    """Endpoint para obtener un curso por id"""
    course = services.get_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

from sqlmodel import func, select
from app.common.database import SessionDeep
from app.courses.models import Course
from app.enrollments.models import Enrollment


def get_analytics_data(db: SessionDeep, instructor_id: str = None):
    """
    Function to get analytics data.
    """
    # Placeholder for actual analytics data retrieval logic
    """
    SELECT 
  c.id AS course_id,
  c.title AS "Titulo curso",
  c.category AS category,
  COUNT(e.id) AS "numero de estudiantes"
FROM 
  course AS c
LEFT JOIN 
  enrollment AS e 
ON 
  c.id = e.course_id
WHERE
  c.instructor_id = 1
GROUP BY 
  c.id, c.title
ORDER BY
  c.id ASC;
  """

    statement = (
        select(
            Course.id.label("course_id"),
            Course.title.label("course_title"),
            Course.category.label("category"),
            func.count(Enrollment.id).label("number_of_students"),
        )
        .outerjoin(Enrollment, Course.id == Enrollment.course_id)
        .where(Course.instructor_id == int(instructor_id))
        .group_by(Course.id, Course.title, Course.category)
        .order_by(Course.id.asc())
    )

    results = db.exec(statement).all()

    if not results:
        return []

    response = [
        {
            "course_id": course_id,
            "course_title": course_title,
            "category": category,
            "number_of_students": number_of_students,
        }
        for course_id, course_title, category, number_of_students in results
    ]
    return response


def get_analytics_totals(db: SessionDeep, instructor_id: str):
    """
    Function to get total number of courses and students for an instructor.
    """
    # Contar cursos
    total_courses = db.exec(
        select(func.count()).select_from(Course).where(Course.instructor_id == int(instructor_id))
    ).one()

    # Contar estudiantes en todos sus cursos
    total_students = db.exec(
        select(func.count(Enrollment.id))
        .join(Course, Enrollment.course_id == Course.id)
        .where(Course.instructor_id == int(instructor_id))
    ).one()

    return {
        "total_courses": total_courses,
        "total_students": total_students
    }



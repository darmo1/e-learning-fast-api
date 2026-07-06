from sqlmodel import func, select
from app.common.config import platform_fee_pct
from app.common.database import SessionDeep
from app.courses.models import Course
from app.enrollments.models import Enrollment
from app.payments.models import Order, OrderStatus


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


def get_instructor_earnings(db: SessionDeep, instructor_id: int) -> dict:
    """Ganancias del instructor: ventas aprobadas menos la comisión de la
    plataforma, por curso y en total."""
    pct = platform_fee_pct()

    rows = db.exec(
        select(
            Course.id,
            Course.title,
            func.count(Order.id).label("sales"),
            func.coalesce(func.sum(Order.amount), 0).label("gross"),
        )
        .join(Order, Order.course_id == Course.id)
        .where(
            Course.instructor_id == instructor_id,
            Order.status == OrderStatus.approved,
        )
        .group_by(Course.id, Course.title)
        .order_by(func.coalesce(func.sum(Order.amount), 0).desc())
    ).all()

    courses = []
    total_sales, total_gross = 0, 0.0
    for course_id, title, sales, gross in rows:
        gross = float(gross)
        net = round(gross * (1 - pct / 100), 2)
        courses.append(
            {
                "course_id": course_id,
                "title": title,
                "sales": sales,
                "gross": gross,
                "net": net,
            }
        )
        total_sales += sales
        total_gross += gross

    fee = round(total_gross * pct / 100, 2)
    return {
        "platform_fee_pct": pct,
        "totals": {
            "sales": total_sales,
            "gross": round(total_gross, 2),
            "fee": fee,
            "net": round(total_gross - fee, 2),
        },
        "courses": courses,
    }



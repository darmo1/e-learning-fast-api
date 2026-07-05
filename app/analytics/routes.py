from fastapi import APIRouter, Depends

from app.analytics.schemas import CourseAnalyticsOut
from app.analytics.services import get_analytics_data, get_analytics_totals
from app.auth.dependencies import require_role
from app.common.database import SessionDeep
from app.users.models import User, UserRole


analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


@analytics_router.get("/instructor/courses")
async def get_analytics(
    db: SessionDeep,
    current_user: User = Depends(require_role(UserRole.instructor)),
):
    """Analítica por curso del instructor autenticado."""
    return get_analytics_data(db, current_user.id)


@analytics_router.get("/instructor/summary")
def analytics_summary(
    db: SessionDeep,
    current_user: User = Depends(require_role(UserRole.instructor)),
):
    return get_analytics_totals(db, current_user.id)
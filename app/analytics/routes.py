from fastapi import APIRouter, Depends

from app.analytics.schemas import CourseAnalyticsOut
from app.analytics.services import get_analytics_data, get_analytics_totals
from app.auth.dependencies import get_current_user
from app.common.database import SessionDeep


analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


@analytics_router.get("/instructor/courses")
async def get_analytics(
    db: SessionDeep,
    token_data: dict = Depends(get_current_user),
):
    """
    Endpoint to get analytics data.
    """
    print("Analytics endpoint called")
    instructor_id = token_data.id
  
  


    courses =  get_analytics_data(db, instructor_id)
    return courses


@analytics_router.get("/instructor/summary")
def analytics_summary(
    db: SessionDeep,
    token_data: dict = Depends(get_current_user),
):
    instructor_id = token_data.id
    return get_analytics_totals(db, instructor_id)
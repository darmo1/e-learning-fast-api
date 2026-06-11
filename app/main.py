from dotenv import load_dotenv

load_dotenv()
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.analytics.routes import analytics_router
from app.auth.routes import auth_router
from app.auth.utils import is_dev
from app.checkout.routes import checkout_router
from app.comments.routes import comments_router
from app.companies.routes import companies_router
from app.common.database import create_all_tables, engine
from app.courses.routes import course_router
from app.enrollments.routes import enrollment_router
from app.lessons.routes import lessons_router
from app.payments.routes import payments_router
from app.users.routes import user_router

allowed_origins = [
    origin
    for origin in [os.getenv("HOST_FRONTEND"), "https://goproclass.vercel.app"]
    if origin
]

# Swagger/OpenAPI solo en desarrollo
app = FastAPI(
    docs_url="/docs" if is_dev() else None,
    redoc_url="/redoc" if is_dev() else None,
    openapi_url="/openapi.json" if is_dev() else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

create_all_tables(app)
api_v1 = "/api/v1"

app.include_router(user_router, prefix=api_v1, tags=["users"])
app.include_router(course_router, prefix=api_v1, tags=["courses"])
app.include_router(lessons_router, prefix=api_v1, tags=["lessons"])
app.include_router(comments_router, prefix=api_v1, tags=["comments"])
app.include_router(enrollment_router, prefix=api_v1, tags=["enrollments"])
app.include_router(auth_router, prefix=api_v1, tags=["auth"])
app.include_router(checkout_router, prefix=api_v1, tags=["checkout"])
app.include_router(payments_router, prefix=api_v1, tags=["payments"])
app.include_router(companies_router, prefix=api_v1, tags=["companies"])
app.include_router(analytics_router, prefix=api_v1, tags=["analytics"])


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/healthcheck")
def healthcheck():
    """Healthcheck que toca la BD: el intento de conexión despierta a Neon
    si está suspendida. El FE lo llama al cargar para precalentarla."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "up"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "down"},
        )

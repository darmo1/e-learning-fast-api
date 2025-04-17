from fastapi import FastAPI
from app.auth.activation_service import send_activation_email
from app.users.routes import user_router
from app.courses.routes import course_router
from app.lessons.routes import lessons_router
from app.comments.routes import comments_router
from app.enrollments.routes import enrollment_router
from app.auth.routes import auth_router
from app.checkout.routes import checkout_router
from app.common.database import create_all_tables
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()
import os


database_url = os.getenv("HOST_FRONTEND", "http://localhost:3000")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[database_url],  # Prueba con "*" y luego restríngelo a tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

create_all_tables(app)
print("Directorio de trabajo actual:", os.getcwd())
api_v1= '/api/v1'

app.include_router(user_router, prefix=api_v1, tags=["users"])
app.include_router(course_router, prefix=api_v1, tags=["courses"])
app.include_router(lessons_router, prefix=api_v1, tags=["lessons"])   
app.include_router(comments_router, prefix=api_v1, tags=["comments"])   
app.include_router(enrollment_router, prefix=api_v1, tags=["enrollments"])   
app.include_router(auth_router, prefix=api_v1, tags=["auth"])  
app.include_router(checkout_router, prefix=api_v1, tags=["checkout"]) 


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/healthcheck")
def healthcheck():
    send_activation_email('darmito10@gmail.com', 'token')
    return {"status": "ok"}
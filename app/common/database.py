from sqlmodel import Session, create_engine, SQLModel
from typing import Annotated
from fastapi import Depends, FastAPI
from dotenv import load_dotenv
load_dotenv()
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está definido")

# echo solo en desarrollo: en producción loguea cada query (datos sensibles)
# pool_pre_ping: Neon (serverless) suspende y corta conexiones inactivas del
# pool; sin esto la primera request tras la pausa usa una conexión muerta -> 500
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("ENVIRONMENT", "development").lower() == "development",
    pool_pre_ping=True,
    pool_recycle=300,
)

#Create tables
def create_all_tables(app: FastAPI):
    SQLModel.metadata.create_all(engine)



async def get_session():
    ''' Usamos with para manejar las sesiones de la base de daots usando el contexto with para garantizar que la sesión se cierre correctamente cuando no se necesite'''
    with Session(engine) as session: 
        yield session

SessionDeep =  Annotated[Session, Depends(get_session)]
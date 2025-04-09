from pydantic import BaseModel
from typing import Optional
from sqlmodel import SQLModel

class UserBase(SQLModel):
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    '''Añadimos el campo password para que el usuario pueda registrarse'''
    password: str

class UserOut(UserBase):
    id: int
    is_admin: bool
    is_active: bool

    class Config:
        from_attributes = True #Esta opción permite que los objetos SQLModel se puedan convertir a Pydantic models de manera sencilla
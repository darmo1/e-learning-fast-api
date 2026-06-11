from typing import Optional

from pydantic import EmailStr
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    email: EmailStr
    full_name: Optional[str] = Field(default=None, max_length=120)


class UserCreate(UserBase):
    '''Añadimos el campo password para que el usuario pueda registrarse'''
    password: str = Field(min_length=8, max_length=128)
    # Registro corporativo: token del link de invitación de una empresa
    invite_token: Optional[str] = Field(default=None, max_length=64)


class UserOut(UserBase):
    id: int
    is_admin: bool
    is_active: bool

    class Config:
        from_attributes = True  # Permite convertir objetos SQLModel a este schema

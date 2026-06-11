from typing import Optional, Union

from pydantic import Field
from sqlmodel import SQLModel


class CreatePreferenceRequest(SQLModel):
    """Contrato con el FE (src/services/payments/types.ts).

    El precio real SIEMPRE se lee de la BD por course_id; unit_price del
    cliente solo se usa para detectar desincronización FE/BE, nunca para cobrar.
    """

    product_id: Union[int, str]  # course_id
    title: Optional[str] = None
    unit_price: Optional[float] = None
    quantity: int = Field(default=1, ge=1, le=1)  # un curso por compra


class CreatePreferenceResponse(SQLModel):
    init_point: str
    preference_id: str


class OrderOut(SQLModel):
    id: int
    course_id: int
    amount: float
    currency: str
    status: str

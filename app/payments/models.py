from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


def now_utc():
    return datetime.now(timezone.utc)


class OrderStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"
    refunded = "refunded"
    in_process = "in_process"


class Order(SQLModel, table=True):
    """Orden de compra de un curso. El estado lo actualiza el webhook de Mercado Pago."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    course_id: int = Field(foreign_key="course.id", index=True)
    amount: float
    currency: str = Field(default="COP", max_length=3)
    status: OrderStatus = Field(default=OrderStatus.pending, index=True)
    # Identificadores de Mercado Pago
    preference_id: Optional[str] = Field(default=None, index=True)
    payment_id: Optional[str] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)

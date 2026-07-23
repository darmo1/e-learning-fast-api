import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone

import mercadopago
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlmodel import Session, select

from app.courses.models import Course
from app.enrollments.models import Enrollment
from app.feature_flags.services import is_enabled as flag_is_enabled
from app.payments.models import Order, OrderStatus
from app.users.models import User

SANDBOX_FLAG_KEY = "ff-checkout-mercado-pago-sandbox"

load_dotenv()
logger = logging.getLogger(__name__)

MP_ACCESS_TOKEN = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
MP_WEBHOOK_SECRET = os.getenv("MERCADOPAGO_WEBHOOK_SECRET")
CURRENCY_ID = os.getenv("MERCADOPAGO_CURRENCY_ID", "COP")
FRONTEND_URL = (os.getenv("HOST_FRONTEND") or "http://localhost:3000").rstrip("/")
BACKEND_URL = (os.getenv("HOST_BACKEND") or "http://localhost:3005").rstrip("/")

# Estados de pago de MP -> estados de orden nuestros
_MP_STATUS_MAP = {
    "approved": OrderStatus.approved,
    "rejected": OrderStatus.rejected,
    "cancelled": OrderStatus.cancelled,
    "refunded": OrderStatus.refunded,
    "charged_back": OrderStatus.refunded,
    "in_process": OrderStatus.in_process,
    "pending": OrderStatus.pending,
}


def _get_sdk() -> mercadopago.SDK:
    if not MP_ACCESS_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Pasarela de pagos no configurada (MERCADOPAGO_ACCESS_TOKEN)",
        )
    return mercadopago.SDK(MP_ACCESS_TOKEN)


def _enroll_if_needed(db: Session, order: Order) -> None:
    existing = db.exec(
        select(Enrollment).where(
            Enrollment.user_id == order.user_id,
            Enrollment.course_id == order.course_id,
        )
    ).first()
    if not existing:
        db.add(Enrollment(user_id=order.user_id, course_id=order.course_id))
        logger.info(
            "Usuario %s inscrito en curso %s por orden %s",
            order.user_id, order.course_id, order.id,
        )


def _approve_order_in_sandbox(db: Session, order: Order) -> dict:
    """Flag ff-checkout-mercado-pago-sandbox apagada: aprueba la orden al
    instante sin llamar a Mercado Pago e inscribe al usuario, para poder
    probar la compra completa en desarrollo sin credenciales reales."""
    fake_id = f"sandbox-{order.id}"
    order.status = OrderStatus.approved
    order.preference_id = fake_id
    order.payment_id = fake_id
    order.updated_at = datetime.now(timezone.utc)
    db.add(order)
    _enroll_if_needed(db, order)
    db.commit()

    logger.info(
        "Orden %s aprobada por sandbox (flag %s apagada), user=%s course=%s",
        order.id, SANDBOX_FLAG_KEY, order.user_id, order.course_id,
    )

    init_point = (
        f"{FRONTEND_URL}/checkout/success"
        f"?status=approved&external_reference={order.id}&payment_id={fake_id}"
    )
    return {"init_point": init_point, "preference_id": fake_id}


def create_checkout_preference(db: Session, course_id: int, user: User) -> dict:
    """Crea la orden local y la preferencia de Checkout Pro en Mercado Pago."""
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # El precio se toma de la BD, nunca del cliente
    if course.price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Este curso es gratuito, usa la inscripción directa",
        )

    already = db.exec(
        select(Enrollment).where(
            Enrollment.user_id == user.id, Enrollment.course_id == course.id
        )
    ).first()
    if already:
        raise HTTPException(status_code=409, detail="Ya estás inscrito en este curso")

    order = Order(
        user_id=user.id,
        course_id=course.id,
        amount=course.price,
        currency=CURRENCY_ID,
        status=OrderStatus.pending,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    if not flag_is_enabled(db, SANDBOX_FLAG_KEY, default=True):
        return _approve_order_in_sandbox(db, order)

    preference_data = {
        "items": [
            {
                "id": str(course.id),
                "title": course.title,
                "quantity": 1,
                "unit_price": float(course.price),
                "currency_id": CURRENCY_ID,
            }
        ],
        "payer": {"email": user.email},
        "external_reference": str(order.id),
        "back_urls": {
            "success": f"{FRONTEND_URL}/checkout/success",
            "failure": f"{FRONTEND_URL}/checkout/failure",
            "pending": f"{FRONTEND_URL}/checkout/pending",
        },
        "auto_return": "approved",
        "notification_url": f"{BACKEND_URL}/api/v1/payments/webhook",
        "metadata": {
            "order_id": order.id,
            "user_id": user.id,
            "course_id": course.id,
        },
    }

    sdk = _get_sdk()
    try:
        result = sdk.preference().create(preference_data)
    except Exception:
        logger.exception("Error llamando a Mercado Pago para la orden %s", order.id)
        raise HTTPException(status_code=502, detail="Error comunicándose con la pasarela de pago")

    if result.get("status") not in (200, 201):
        logger.error(
            "Mercado Pago rechazó la preferencia (orden %s): %s",
            order.id,
            result.get("response"),
        )
        raise HTTPException(status_code=502, detail="La pasarela de pago rechazó la solicitud")

    preference = result["response"]
    order.preference_id = preference["id"]
    order.updated_at = datetime.now(timezone.utc)
    db.add(order)
    db.commit()

    logger.info(
        "Preferencia MP creada: orden=%s preference=%s user=%s course=%s",
        order.id, preference["id"], user.id, course.id,
    )

    return {"init_point": preference["init_point"], "preference_id": preference["id"]}


def verify_webhook_signature(
    x_signature: str | None, x_request_id: str | None, data_id: str | None
) -> bool:
    """Valida la firma HMAC del webhook de Mercado Pago (header x-signature).

    Formato del header: "ts=<timestamp>,v1=<hmac>"; el manifiesto firmado es
    "id:<data.id>;request-id:<x-request-id>;ts:<ts>;"
    """
    if not MP_WEBHOOK_SECRET:
        # Sin secret configurado no se puede validar la firma; la seguridad
        # recae en que el pago se consulta server-to-server contra la API de MP
        return True
    if not x_signature:
        return False

    parts = dict(
        part.strip().split("=", 1) for part in x_signature.split(",") if "=" in part
    )
    ts, v1 = parts.get("ts"), parts.get("v1")
    if not ts or not v1:
        return False

    manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
    expected = hmac.new(
        MP_WEBHOOK_SECRET.encode(), manifest.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, v1)


def process_payment_notification(db: Session, payment_id: str) -> None:
    """Consulta el pago contra la API de MP (fuente de verdad), actualiza la
    orden y, si quedó aprobado, inscribe al usuario en el curso. Idempotente."""
    sdk = _get_sdk()
    try:
        result = sdk.payment().get(payment_id)
    except Exception:
        logger.exception("Error consultando el pago %s en Mercado Pago", payment_id)
        return

    if result.get("status") != 200:
        logger.error("MP no devolvió el pago %s: %s", payment_id, result.get("response"))
        return

    payment = result["response"]
    mp_status = payment.get("status")
    external_reference = payment.get("external_reference")

    logger.info(
        "Webhook MP: payment=%s status=%s external_reference=%s",
        payment_id, mp_status, external_reference,
    )

    if not external_reference:
        logger.warning("Pago %s sin external_reference, se ignora", payment_id)
        return

    try:
        order_id = int(external_reference)
    except ValueError:
        logger.warning("external_reference no numérico en pago %s: %r", payment_id, external_reference)
        return

    order = db.get(Order, order_id)
    if not order:
        logger.warning("Orden %s del pago %s no existe", order_id, payment_id)
        return

    new_status = _MP_STATUS_MAP.get(mp_status, OrderStatus.pending)

    # Idempotencia: si ya está aprobada no se reprocesa
    if order.status == OrderStatus.approved and new_status == OrderStatus.approved:
        logger.info("Orden %s ya aprobada, webhook duplicado ignorado", order.id)
        return

    order.status = new_status
    order.payment_id = str(payment_id)
    order.updated_at = datetime.now(timezone.utc)
    db.add(order)

    if new_status == OrderStatus.approved:
        _enroll_if_needed(db, order)

    db.commit()

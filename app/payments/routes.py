import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.common.database import SessionDeep, engine
from app.payments import services
from app.payments.schemas import CreatePreferenceRequest, CreatePreferenceResponse
from app.users.models import User

logger = logging.getLogger(__name__)

payments_router = APIRouter(prefix="/payments", tags=["payments"])


@payments_router.post("/create-preference", response_model=CreatePreferenceResponse)
async def create_preference(
    body: CreatePreferenceRequest,
    db: SessionDeep,
    current_user: User = Depends(get_current_user),
):
    """Crea una preferencia de Checkout Pro para comprar un curso.

    El cliente solo indica QUÉ curso (product_id); el precio se lee de la BD.
    """
    try:
        course_id = int(body.product_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="product_id inválido")

    return services.create_checkout_preference(db, course_id, current_user)


def _process_notification(payment_id: str):
    """Tarea en background: usa una sesión propia porque la del request ya se cerró."""
    try:
        with Session(engine) as db:
            services.process_payment_notification(db, payment_id)
    except Exception:
        logger.exception("Error procesando notificación de pago %s", payment_id)


@payments_router.post("/webhook")
async def mercadopago_webhook(request: Request, background_tasks: BackgroundTasks):
    """Webhook público de Mercado Pago.

    Responde 200 de inmediato y procesa en background. La fuente de verdad es
    la consulta server-to-server del pago contra la API de MP, nunca el body.
    """
    params = request.query_params
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass  # MP a veces manda body vacío en IPN

    # Formato webhook: ?type=payment&data.id=123 / body {"type": "payment", "data": {"id": ...}}
    # Formato IPN legado: ?topic=payment&id=123
    notification_type = params.get("type") or params.get("topic") or body.get("type")
    data_id = (
        params.get("data.id")
        or params.get("id")
        or (body.get("data") or {}).get("id")
    )

    logger.info("Webhook MP recibido: type=%s data_id=%s", notification_type, data_id)

    if not services.verify_webhook_signature(
        request.headers.get("x-signature"),
        request.headers.get("x-request-id"),
        str(data_id) if data_id is not None else None,
    ):
        logger.warning("Webhook MP con firma inválida (data_id=%s)", data_id)
        raise HTTPException(status_code=401, detail="Firma inválida")

    if notification_type == "payment" and data_id:
        background_tasks.add_task(_process_notification, str(data_id))
    else:
        # merchant_order, plan, etc. — se aceptan y se ignoran
        logger.info("Webhook MP ignorado (type=%s)", notification_type)

    return {"status": "received"}

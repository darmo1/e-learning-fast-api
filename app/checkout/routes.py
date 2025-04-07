from fastapi import APIRouter, Header, Request
import json
import stripe
import stripe.webhook

from app.checkout.services import webhook_stripe
from app.common.database import SessionDeep


checkout_router = APIRouter(prefix="/checkout", tags=["checkout"])


@checkout_router.post("/webhook")
async def checkout_stripe(
    request: Request,
    db: SessionDeep,
    stripe_signature: str = Header(None),  # Firma enviada por Stripe
):
    payload = await request.body()
    data = payload.decode("utf-8")  # Decodificar el JSON recibido
    stripe_signature = request.headers.get("stripe-signature") 

    return webhook_stripe(payload, stripe_signature, db)

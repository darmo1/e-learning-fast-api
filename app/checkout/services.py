import os
from fastapi import HTTPException
import stripe
from dotenv import load_dotenv

#cargar variables de entorno
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")



def webhook_stripe(payload, stripe_signature, db):
    """
    Procesa los eventos del webhook de Stripe y guarda la información en la BD.
    """
    try:
        event = stripe.Webhook.construct_event(payload,stripe_signature, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Firma no válida")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error procesando el webhook: {str(e)}")
    
    event_type = event.get("type", "")
    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        stripe_customer_id = session["customer"]
        stripe_subscription_id = session.get("subscription", None)

 

    return {"message": "Webhook procesado"}
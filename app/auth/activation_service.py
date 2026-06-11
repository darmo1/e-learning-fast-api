import logging
import os
import smtplib
from email.message import EmailMessage

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _send_via_brevo(to: str, subject: str, body: str):
    """Envío por la API HTTP de Brevo (preferido: los hostings serverless
    suelen bloquear puertos SMTP; la API va por 443)."""
    api_key = os.getenv("BREVO_API_KEY")
    sender_email = os.getenv("EMAIL_SENDER")
    sender_name = os.getenv("EMAIL_SENDER_NAME", "GoProClass")

    response = requests.post(
        BREVO_API_URL,
        headers={"api-key": api_key, "content-type": "application/json"},
        json={
            "sender": {"email": sender_email, "name": sender_name},
            "to": [{"email": to}],
            "subject": subject,
            "textContent": body,
        },
        timeout=10,
    )
    if response.status_code >= 300:
        raise RuntimeError(
            f"Brevo rechazó el envío ({response.status_code}): {response.text[:300]}"
        )
    logger.info("Email enviado a %s vía Brevo (%s)", to, response.status_code)


def _send_via_gmail_smtp(to: str, subject: str, body: str):
    """Fallback legado: SMTP de Gmail con app password."""
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    if not sender or not password:
        raise RuntimeError("EMAIL_SENDER/EMAIL_PASSWORD no configurados")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)


def _send_email(to: str, subject: str, body: str):
    if os.getenv("BREVO_API_KEY"):
        _send_via_brevo(to, subject, body)
    else:
        _send_via_gmail_smtp(to, subject, body)


def send_activation_email(email: str, token: str):
    """Envía un correo con el link de activación de la cuenta"""
    base_url = os.getenv("HOST_BACKEND", "http://localhost:3005")
    activation_link = f"{base_url}/api/v1/auth/activate/{token}"
    _send_email(
        email,
        "Activa tu cuenta",
        f"Haz clic en este enlace para activar tu cuenta: {activation_link}",
    )


def send_password_reset_email(email: str, token: str):
    """Envía el link de restablecimiento de contraseña (página del frontend)."""
    base_url = os.getenv("HOST_FRONTEND", "http://localhost:3000")
    reset_link = f"{base_url}/reset-password?token={token}"
    _send_email(
        email,
        "Restablece tu contraseña",
        "Recibimos una solicitud para restablecer tu contraseña.\n\n"
        f"Haz clic en este enlace (válido por 30 minutos): {reset_link}\n\n"
        "Si no fuiste tú, ignora este correo: tu contraseña no cambia.",
    )

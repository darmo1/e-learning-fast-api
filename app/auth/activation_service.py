import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def send_activation_email(email: str, token: str):
    """Envía un correo con el link de activación de la cuenta"""
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    if not sender or not password:
        raise RuntimeError("EMAIL_SENDER/EMAIL_PASSWORD no configurados")

    base_url = os.getenv("HOST_BACKEND", "http://localhost:3005")
    activation_link = f"{base_url}/api/v1/auth/activate/{token}"

    msg = EmailMessage()
    msg["Subject"] = "Activa tu cuenta"
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(f"Haz clic en este enlace para activar tu cuenta: {activation_link}")

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)

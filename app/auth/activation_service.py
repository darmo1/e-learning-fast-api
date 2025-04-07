import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv


def send_activation_email(email: str, token: str):
    load_dotenv()
    """Envía un correo con el link de activación de la cuenta"""
    msg = EmailMessage()
    msg["Subject"] = "Activa tu cuenta"
    msg["From"] = os.getenv("EMAIL_SENDER")
    msg["To"] = email
    activation_link = f"http://localhost:8000/auth/activate/{token}"
    msg.set_content(f"Haz clic en este enlace para activar tu cuenta: {activation_link}")

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(os.getenv("EMAIL_SENDER"), os.getenv("EMAIL_PASSWORD"))
        server.send_message(msg)



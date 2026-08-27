import os
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode

def send_order_confirmation(recipient: str, order_id: int, token: str):
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM")
    if not host or not sender:
        raise RuntimeError("Email is not configured. Set SMTP_HOST and SMTP_FROM.")

    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost").rstrip("/")
    confirmation_url = f"{frontend_url}/confirm-order?{urlencode({'token': token})}"
    message = EmailMessage()
    message["Subject"] = f"Confirm your order #{order_id}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"Please confirm your order by opening this link:\n\n{confirmation_url}\n\n"
        "This link expires in 30 minutes."
    )

    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        if os.getenv("SMTP_USE_TLS", "true").lower() == "true":
            smtp.starttls()
        if username:
            smtp.login(username, password or "")
        smtp.send_message(message)

def send_account_verification(recipient: str, token: str):
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM")
    if not host or not sender:
        raise RuntimeError("Email is not configured. Set SMTP_HOST and SMTP_FROM.")
    frontend_url = os.getenv("FRONTEND_BASE_URL", "http://localhost").rstrip("/")
    verification_url = f"{frontend_url}/verify-email?{urlencode({'token': token})}"
    message = EmailMessage()
    message["Subject"] = "Verify your account"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(f"Verify your account by opening this link:\n\n{verification_url}\n\nThis link expires in 30 minutes.")
    port = int(os.getenv("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        if os.getenv("SMTP_USE_TLS", "true").lower() == "true": smtp.starttls()
        if os.getenv("SMTP_USERNAME"):
            smtp.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD", ""))
        smtp.send_message(message)

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings


logger = logging.getLogger(__name__)


def send_email(recipient: str, subject: str, body: str) -> bool:
    """Send a plain-text email when SMTP is configured; never raise to callers."""
    host = (settings.smtp_host or "").strip()
    sender = (settings.smtp_from_email or "").strip()
    if not host or not sender:
        logger.info("Email not sent because SMTP_HOST or SMTP_FROM_EMAIL is not configured")
        return False
    username = (settings.smtp_username or "").strip()
    password = settings.smtp_password.get_secret_value() if settings.smtp_password else ""
    if bool(username) != bool(password):
        logger.warning("Email not sent because SMTP_USERNAME and SMTP_PASSWORD must be configured together")
        return False

    try:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((settings.smtp_from_name, sender))
        message["To"] = recipient
        message.set_content(body)
        context = ssl.create_default_context()
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(host, settings.smtp_port, timeout=settings.smtp_timeout_seconds, context=context) as client:
                if username:
                    client.login(username, password)
                client.send_message(message)
        else:
            with smtplib.SMTP(host, settings.smtp_port, timeout=settings.smtp_timeout_seconds) as client:
                client.ehlo()
                if settings.smtp_use_tls:
                    client.starttls(context=context)
                    client.ehlo()
                if username:
                    client.login(username, password)
                client.send_message(message)
        return True
    except Exception as exc:
        # Do not log exception text: SMTP errors can include server details.
        logger.warning("Email delivery failed (%s)", type(exc).__name__)
        return False

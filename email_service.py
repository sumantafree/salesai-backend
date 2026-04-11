"""
Email Service
- Sends emails via SMTP (Gmail, Outlook, etc.)
- Configure SMTP settings in config.env
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")


def send_email(to_email: str, subject: str, body: str) -> dict:
    """Send an email. Returns success/failure result."""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return {
            "success": False,
            "message": "SMTP not configured. Add SMTP_EMAIL and SMTP_PASSWORD to config.env to enable email sending."
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email

        # Plain text version
        text_part = MIMEText(body, "plain")
        msg.attach(text_part)

        # HTML version (simple formatting)
        html_body = body.replace("\n", "<br>")
        html_part = MIMEText(f"<html><body><p>{html_body}</p></body></html>", "html")
        msg.attach(html_part)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())

        return {"success": True, "message": f"Email sent to {to_email}"}

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "SMTP authentication failed. Check your email and app password in config.env."
        }
    except Exception as e:
        return {"success": False, "message": f"Email failed: {str(e)}"}

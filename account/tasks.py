from celery import shared_task
import requests
import logging
from django.utils import timezone
from datetime import timedelta
from .models import OneTimePassword
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

@shared_task
def send_otp_email(user, user_email, otp_code):
    """
    Sends an OTP email to the given user using Mailgun.
    Expects `user` to be a dict with keys: 'first_name' and 'last_name'.
    """
    current_site = "Backvia.com"
    email_subject = "Verify your email with this OTP"

    context = {
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "email": user_email,
        "otp_code": otp_code,
        "site_name": current_site,
        "support_email": "support@backvia.com",
    }

    text_content = render_to_string("email/otp_mail.txt", context)
    html_content = render_to_string("email/otp_mail.html", context)

    try:
        response = requests.post(
            f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
            auth=("api", settings.MAILGUN_API_KEY),
            data={
                "from": f"Mailgun Sandbox <{settings.DEFAULT_FROM_EMAIL}>",
                "to": [user_email],
                "subject": email_subject,
                "text": text_content,
                "html": html_content,
            }
        )
        response.raise_for_status()
        logger.info(f"OTP email sent successfully to {user_email}")
        return {"status": "success", "message": "OTP sent successfully"}

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send OTP to {user_email} via Mailgun: {str(e)}")
        return {"status": "error", "message": "Failed to send OTP"}




@shared_task
def cleanup_expired_otps():
    """
    Periodically delete expired OTPs.
    """
    expiration_time = timezone.now() - timezone.timedelta(minutes=5)
    deleted, _ = OneTimePassword.objects.filter(created_at__lt=expiration_time).delete()
    return f"Deleted {deleted} expired OTPs."
import secrets
import logging
from django.utils import timezone
from django.conf import settings
from .models import User, OneTimePassword
from .tasks import send_otp_email  # Assuming you have a task to send the OTP email

logger = logging.getLogger(__name__)



def generate_otp():
    """Generate a cryptographically secure 6-digit OTP."""
    return ''.join(secrets.choice('0123456789') for _ in range(6))




def create_otp_for_user(user):
    """
    Generate and store OTP for a user.
    Overwrites any existing OTP.
    """
    try:
        user = User.objects.get(email=user.email)
    except User.DoesNotExist:
        return {"status": "error", "message": "User not found"}

    if user.is_verified and user.is_active:
        return {"status": "error", "message": "User already verified"}

    otp_code = generate_otp()

    try:
        OneTimePassword.objects.update_or_create(
            user=user,
            defaults={
                'code': otp_code,
                'created_at': timezone.now(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to save OTP for {user.email}: {str(e)}")
        return {"status": "error", "message": "Failed to save OTP"}

    user_data = {
        "first_name": user.first_name,
        "last_name": user.last_name,
    }
    send_otp_email.delay(user_data, user.email, otp_code)

    return {"status": "success", "message": "OTP created", "otp": otp_code}

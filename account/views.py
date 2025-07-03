from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from .serializers import RegistrationSerializer,LoginSerializer,VerifyOTPSerializer, ResendOTPSerializer, LogoutSerializer, PasswordResetSerializer,UserProfileSerializer
from .utils import create_otp_for_user
from django.contrib.auth.tokens import default_token_generator
# from django_rest_passwordreset.signals import reset_password_token_created
# from django_rest_passwordreset.models import ResetPasswordToken
# JWT authentication imports
from rest_framework_simplejwt.tokens import RefreshToken 
from rest_framework_simplejwt.exceptions import TokenError
from .models import *
import logging

logger = logging.getLogger(__name__)

from django.contrib.auth import get_user_model
User = get_user_model()



@api_view(['POST'])
def registration_view(request):
    """
    Handles user registration.
   
    """

    serializer = RegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    create_otp_for_user(user)  # Generate and send OTP to the user

    return Response(
        {
            'message': 'Registration successful',
            'user': serializer.data
        },
        status=status.HTTP_201_CREATED
    )








# @api_view(['POST'])
# def code_verification(request):
#     """Verify OTP code."""
#     serializer = VerifyOTPSerializer(data=request.data)
#     if not serializer.is_valid():
#         return Response(
#             {"message": serializer.errors.get('code', ['Invalid input'])[0]},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     # Get user and OTP from serializer context
#     user = serializer.context['user']
#     otp = serializer.context['otp']

#     user.is_verified = True
#     user.save()
#     otp.delete()  # Clean up OTP after verification

#     return Response(
#         {"message": "Account email verified successfully"},
#         status=status.HTTP_200_OK
#     )





# @api_view(['POST'])
# def resend_otp(request):
#     """Resend OTP to user's email."""
#     serializer = ResendOTPSerializer(data=request.data)
#     if not serializer.is_valid():
#         return Response(
#             {"message": serializer.errors.get('email', ['Invalid input'])[0]},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     # Get email from validated data
#     email = serializer.validated_data['email']
#     result = send_code_to_user(email)
#     if result["status"] == "error":
#         status_code = (
#             status.HTTP_400_BAD_REQUEST
#             if result["message"] in ["User does not exist", "User already verified"]
#             else status.HTTP_500_INTERNAL_SERVER_ERROR
#         )
#         return Response(
#             {"message": result["message"]},
#             status=status_code
#         )

#     return Response(
#         {"message": result["message"]},
#         status=status.HTTP_200_OK
#     )







@api_view(['POST'])
def login_view(request):
    """
    Handles user login via POST request and returns JWT tokens.
    """
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid(raise_exception=True):
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            "full_name": f"{user.first_name} {user.last_name}",
            "user_id": user.id,
            "email": user.email,
            "is_verified": user.is_verified,
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    





@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logs out a user by blacklisting their refresh token."""
    serializer = LogoutSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"message": serializer.errors.get('refresh', ['Invalid input'])[0]},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Blacklist the refresh token
        serializer.save()

        # Clean up any existing OTP for the user
        OneTimePassword.objects.filter(user=request.user).delete()

        return Response(
            {"message": "Successfully logged out"},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Logout failed for user {request.user.email}: {str(e)}")
        return Response(
            {"message": "An error occurred during logout"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    





# @api_view(['POST'])
# def password_reset_request(request):
#     """Request a password reset by validating the email and generating a token."""
#     serializer = PasswordResetSerializer(data=request.data)
#     if not serializer.is_valid():
#         logger.warning(f"Invalid password reset request: {serializer.errors}")
#         return Response(
#             {"message": serializer.errors.get('email', ['Invalid input'])[0]},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     email = serializer.validated_data['email']
#     try:
#         user = User.objects.get(email=email)
#         # Create reset token
#         token = ResetPasswordToken.objects.create(user=user)
#         logger.info(f"Password reset token created for {email}")

#         # 🔥 Manually trigger the signal
#         reset_password_token_created.send(
#             sender=ResetPasswordToken,
#             instance=request,  # or your serializer if preferred
#             reset_password_token=token
#         )

#         return Response(
#             {"message": "Password reset email sent successfully"},
#             status=status.HTTP_200_OK
#         )
#     except Exception as e:
#         logger.error(f"Failed to create password reset token for {email}: {str(e)}")
#         return Response(
#             {"message": "An error occurred while processing your request"},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile_view(request, user_id):
    """View user profile information."""
    try:
        user = User.objects.get(id=user_id)
        profile = user.userprofile 
    except User.DoesNotExist:
        return Response({"message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    except UserProfile.DoesNotExist:
        return Response({"message": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserProfileSerializer(profile)
    return Response(serializer.data, status=status.HTTP_200_OK)





@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def update_profile(request, user_id):
    """Update user profile using user_id."""
    try:
        user = User.objects.get(id=user_id)
        profile = user.userprofile
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    except UserProfile.DoesNotExist:
        return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserProfileSerializer(profile, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

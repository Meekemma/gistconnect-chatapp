from rest_framework import serializers
from .models import *
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from django.contrib.auth import get_user_model

User = get_user_model() 



class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(style={'input_type': 'password'}, write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True, required=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name','username', 'password', 'password2')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        validate_password(attrs['password'])
        return attrs
    

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")

        return value

    def create(self, validated_data):
        validated_data.pop('password2')
        validated_data['email'] = validated_data['email'].lower()
        user = User(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            username=validated_data['username']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(style={'input_type': 'password'}, write_only=True, required=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email:
            email = email.lower()

        if email and password:
            # Attempt to authenticate the user with provided credentials
            user = authenticate(request=self.context.get('request'), email=email, password=password)
            if not user:
                raise serializers.ValidationError("Invalid credentials.", code='authorization')
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            if not user.is_verified:
                raise serializers.ValidationError("Email is not verified.")
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")

        attrs['user'] = user  # Attach the authenticated user to the validated data
        attrs['email'] = email
        return attrs





class VerifyOTPSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)

    def validate_code(self, value):
        """Validate the OTP code."""
        if not isinstance(value, str):
            raise serializers.ValidationError("OTP must be a string of 6 digits")
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits")

        try:
            otp = OneTimePassword.objects.get(code=value)
        except OneTimePassword.DoesNotExist:
            raise serializers.ValidationError("Invalid OTP code")

        if not otp.is_valid():
            otp.delete()
            raise serializers.ValidationError("OTP has expired")

        if otp.user.is_verified:
            raise serializers.ValidationError("User already verified")

        # Store OTP and user for use in the view
        self.context['otp'] = otp
        self.context['user'] = otp.user
        return value

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate the email and enforce rate limiting."""
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")

        if user.is_verified:
            raise serializers.ValidationError("User already verified")

        # Check for recent OTP (rate limiting: 1 request per 60 seconds)
        try:
            recent_otp = OneTimePassword.objects.get(user=user)
            if timezone.now() - recent_otp.created_at < timezone.timedelta(seconds=60):
                raise serializers.ValidationError("Please wait 60 seconds before requesting a new OTP")
        except OneTimePassword.DoesNotExist:
            pass  # No recent OTP, proceed

        # Store user for use in the view
        self.context['user'] = user
        return value






class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate_refresh(self, value):
        """Validate the refresh token."""
        if not value.strip():
            raise serializers.ValidationError("Refresh token cannot be empty")
        
        try:
            # Verify the token is a valid refresh token
            token = RefreshToken(value)
            return value
        except TokenError:
            raise serializers.ValidationError("Invalid or expired refresh token")

    def save(self):
        """Blacklist the refresh token."""
        try:
            token = RefreshToken(self.validated_data['refresh'])
            token.blacklist()
        except TokenError as e:
            raise serializers.ValidationError(f"Failed to blacklist token: {str(e)}")
        




class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate that the email belongs to a registered user."""
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address")
        
        # Optional: Require verified users
        if not user.is_verified:
            raise serializers.ValidationError("User email is not verified")

        return value





class UserProfileSerializer(serializers.ModelSerializer):
    referral_url = serializers.ReadOnlyField()

    class Meta:
        model = UserProfile
        fields = [
                    'user', 
                    'first_name', 
                    'last_name', 
                    'email', 
                    'gender',  
                    'phone_number',
                    'profile_picture',
                    'country',
                    'address', 
                    'city', 
                    'state', 
                    'bio'
                ]
        read_only_fields = ['user', 'first_name', 'last_name', 'email', 'referral_code', 'referral_url']


    def update(self, instance, validated_data):
        profile_picture = validated_data.get('profile_picture')
        if profile_picture:
            instance.profile_picture = profile_picture

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
        
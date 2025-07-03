from django.urls import path
from . import views

# from django_rest_passwordreset.views import  reset_password_confirm


# from rest_framework_simplejwt.views import (
#     TokenRefreshView,
# )


urlpatterns = [
    path('registration/', views.registration_view, name='register'),
    # path('verify_code/', views.code_verification, name='verify_code'),
    # path('resend_otp/', views.resend_otp, name='resend_otp'),
    path('login/', views.login_view, name='login'),
    # path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # path('logout/', views.logout_view, name='logout'),
    # path('profile/<uuid:user_id>/', views.user_profile_view, name='user_profile'),
    # path('profile_update/<uuid:user_id>/', views.update_profile, name='profile_update'),

    # path('password_reset/', views.password_reset_request, name='reset_password_request_token'),
    # path('api/password_reset/confirm/', reset_password_confirm, name='reset_password_confirm'),

]



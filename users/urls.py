from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegistrationView,
    SendEmailConfirmationView,
    ConfirmEmailView,
    RequestResetPasswordView,
    ResetPasswordView,
    UserProfileView,
    ChangePasswordView,
    ChangingToVendorView,
)

app_name = "users"

urlpatterns = [
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", RegistrationView.as_view(), name="register"),
    path(
        "send-confirmation-email/",
        SendEmailConfirmationView.as_view(),
        name="send_email_confirmation",
    ),
    path(
        "confirm-email/<uuid:token_id>/",
        ConfirmEmailView.as_view(),
        name="confirm_email",
    ),
    path(
        "password-reset/<str:uidb64>/<str:token>/",
        ResetPasswordView.as_view(),
        name="reset-password",
    ),
    path(
        "forgot-password/", RequestResetPasswordView.as_view(), name="forgot-password"
    ),
    path("me/", UserProfileView.as_view(), name="user-profile"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("upgrade-vendor/", ChangingToVendorView.as_view(), name="vendor-permission"),
]

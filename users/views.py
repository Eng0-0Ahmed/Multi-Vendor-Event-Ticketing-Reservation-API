from django.shortcuts import render
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from .serializers import (
    UserRegistrationSerializer,
    RequestPasswordResetSerializer,
    ResetPasswordSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
)
from .models import User, EmailConfirmationToken
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .utils import send_confirmation_email
from rest_framework.response import Response
from .tokens import password_reset_token_generator
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode


class RegistrationView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    queryset = User.objects.all()


class UserProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class SendEmailConfirmationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        user = request.user
        token = EmailConfirmationToken.objects.create(user=user)
        send_confirmation_email(email=user.email, token_id=token.pk, user_id=user.pk)
        return Response(
            data={"detail": "Confirmation email sent successfully!"}, status=201
        )


class ConfirmEmailView(APIView):
    def get(self, request, token_id):
        try:
            token = EmailConfirmationToken.objects.get(pk=token_id)
            if token.is_expired():
                token.delete()
                return Response(data={"detail": "Token has expired"}, status=400)
            user = token.user
            user.is_active = True
            user.save()
            token.delete()
            return Response(
                data={"detail": "Email was verified successfully"}, status=200
            )

        except EmailConfirmationToken.DoesNotExist:
            return Response(
                data={"detail": "Email verification was failed"}, status=400
            )


class RequestResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RequestPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email=email).first()
        if user:
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = password_reset_token_generator.make_token(user)
            reset_url = (
                f"http://localhost:8000/api/users/reset-password/{uidb64}/{token}/"
            )
            send_mail(
                subject="Password Reset Request",
                message=f"Click the link to reset your password: {reset_url}",
                from_email="owner@eventbooking.com",
                recipient_list=[user.email],
            )
        return Response(
            {
                "detail": "If an account with that email exists, a password reset email has been sent."
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"error": "Invalid user ID"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not password_reset_token_generator.check_token(user, token):
            return Response(
                {"error": "Token is invalid or has expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["password"])
        user.save()

        return Response(
            {"detail": "Password has been successfully reset."},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response(
            {"detail": "Password updated successfully."}, status=status.HTTP_200_OK
        )


class ChangingToVendorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.is_organizer:
            return Response(
                {"detail": "User is already an organizer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_organizer = True
        user.save()
        return Response(
            {"detail": "Your permission updated successfully."},
            status=status.HTTP_200_OK,
        )

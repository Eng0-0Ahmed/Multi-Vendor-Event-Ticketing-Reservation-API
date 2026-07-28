from django.core.mail import send_mail


def send_confirmation_email(user_id, token_id, email):
    link = f"http://127.0.0.1:8000/api/users/confirm-email/{token_id}/"

    subject = "Verification email from The Multi-Vendor Event Ticketing & Reservation"
    message = (
        f"thank you for signing up." f"Click the link to activate your account: {link}"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email="ownerwebsite@gmail.com",
        recipient_list=[email],
    )
    print("Email confirmation was sent")

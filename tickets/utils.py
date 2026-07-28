from django.core.mail import EmailMessage

def send_ticket_email(ticket):
    if not ticket.owner or not ticket.owner.email:
        return

    subject = f'Your Ticket for Event #{ticket.ticket_type.ticket_to_event_id}'
    message = (
        f'Hi {ticket.owner.email},\n\n'
        f'Thank you for your purchase! Attached is your QR code ticket for check-in.\n\n'
        f'Ticket ID: {ticket.uuid}\n'
    )
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=None,
        to=[ticket.owner.email],
    )
    if ticket.qr_code:
        ticket.qr_code.open()
        email.attach(
        filename=f'ticket_{ticket.uuid}.png', content=ticket.qr_code.read(), mimetype='image/png',)
        email.send(fail_silently=False)
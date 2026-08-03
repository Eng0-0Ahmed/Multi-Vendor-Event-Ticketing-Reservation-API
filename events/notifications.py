from .models import Event
from tickets.models import Ticket, TicketType
from users.models import User
import json
from notifications.redis_client import get_redis_client
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

now = timezone.now()
in_24h = now + timedelta(hours=24)

def send_24h_event_reminders():
    tickets = Ticket.objects.filter(
        ticket_type__ticket_to_event__event_date__gte=now,
        ticket_type__ticket_to_event__event_date__lte=in_24h,
        ticket_type__ticket_to_event__status="published",
        status="purchased",
        owner__isnull=False,
        ).select_related("owner", "ticket_type__ticket_to_event")
    redis_client = get_redis_client()
    for ticket in tickets:
        event = ticket.ticket_type.ticket_to_event

        payload = {
            "event_type": "EVENT_REMINDER_24H",
            "email": ticket.owner.email,
            "event_title": event.title,
            "event_uuid": str(event.uuid),
            "ticket_uuid": str(ticket.uuid),
            "name": ticket.owner.first_name,
        }
        redis_client.rpush("notifications", json.dumps(payload))


def send_remaining_ticket_promos():
    available_ticket_types = TicketType.objects.filter(
        available_quantity__gte=1,  
        ticket_to_event__event_date__gte=now,
        ticket_to_event__event_date__lte=in_24h,
        ticket_to_event__status="published",
    ).select_related("ticket_to_event")

    redis_client = get_redis_client()

    if not available_ticket_types.exists():
        return
   

    for ticket_type in available_ticket_types:
        event = ticket_type.ticket_to_event
        target_users = User.objects.filter(is_active=True, is_organizer=False).exclude(tickets__ticket_type__ticket_to_event=event)
        for user in target_users:
            payload = {
                "event_type": "PROMO_REMAINING_TICKETS",
                "email": user.email,
                "event_title": event.title,
                "event_uuid": str(event.uuid),
                "ticket_tier": ticket_type.ticket_tier,
                "remaining_tickets": ticket_type.available_quantity,
            }

            redis_client.rpush("notifications", json.dumps(payload))
import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from tickets.models import TicketType
from notifications.redis_client import get_redis_client

@receiver(post_save, sender=TicketType)
def queue_tickettype_upsert(sender, instance, **kwargs):
    payload = {
        "action": "upsert",
        "doc_type": "ticket",
        "uuid": str(instance.uuid),
        "ticket_tier": instance.ticket_tier,
        "event_title": instance.ticket_to_event.title,
        "price": float(instance.price),
        "available_quantity": instance.available_quantity,
        "sales_start_at": instance.sales_start_at.isoformat(),
        "sales_ended_at": instance.sales_ended_at.isoformat(),
        "created_at": instance.created_at.isoformat(),
        "updated_at": instance.updated_at.isoformat(),
    }
    get_redis_client().rpush("vector_sync", json.dumps(payload))
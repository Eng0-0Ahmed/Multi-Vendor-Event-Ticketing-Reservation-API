import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Event
from notifications.redis_client import get_redis_client

@receiver(post_save, sender=Event)
def queue_event_upsert(sender, instance, **kwargs):
    payload = {
        "action": "upsert",
        "doc_type": "event",
        "uuid": str(instance.uuid),
        "title": instance.title,
        "description": instance.description,
        "location": instance.location,
        "status": instance.status,
        "vendor": str(instance.vendor_id),
        "event_date": instance.event_date.isoformat(),
    }
    get_redis_client().rpush("vector_sync", json.dumps(payload))
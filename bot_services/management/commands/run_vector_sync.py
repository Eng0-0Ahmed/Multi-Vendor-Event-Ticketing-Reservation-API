import json
import os
import time
import redis
import redis.exceptions
from django.conf import settings
from django.core.management.base import BaseCommand
from bot_services.schemas import EventSchema, TicketSchema
from bot_services.services.vector_service import (
    upsert_event_to_vector_db,
    upsert_ticket_to_vector_db,
)


def get_redis_url():
    return os.getenv("REDIS_URL") or getattr(settings, "REDIS_URL", "redis://redis:6379/0")


class Command(BaseCommand):
    def handle(self, *args, **options):
        r = redis.Redis.from_url(
            get_redis_url(), decode_responses=True, socket_timeout=None
        )

        self.stdout.write("Listening on vector_sync...")
        while True:
            try:
                item = r.blpop("vector_sync", timeout=5)
                if not item:
                    continue

                _, raw = item
                data = json.loads(raw)

                if data.get("doc_type") == "event":
                    upsert_event_to_vector_db(EventSchema(**data))
                else:
                    upsert_ticket_to_vector_db(TicketSchema(**data))

            except redis.exceptions.TimeoutError:
                continue
            except Exception as e:
                self.stderr.write(f"Error processing vector sync item: {e}")
                time.sleep(1)
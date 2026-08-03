from django.core.management.base import BaseCommand
from events.notifications import (
    send_24h_event_reminders,
    send_remaining_ticket_promos,
)


class Command(BaseCommand):
    help = "Pushes 24h event reminders and ticket promos to Redis"

    def handle(self, *args, **options):
        self.stdout.write("Starting notification batch jobs...")
        send_24h_event_reminders()
        self.stdout.write(self.style.SUCCESS("Successfully processed 24h event reminders."))
        send_remaining_ticket_promos()
        self.stdout.write(self.style.SUCCESS("Successfully processed ticket promos."))
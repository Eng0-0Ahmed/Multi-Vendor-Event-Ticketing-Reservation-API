from django.core.management.base import BaseCommand
from tickets.models import Ticket

class Command(BaseCommand):
  help = 'Releases ticket holds that have exceeded their reservation time.'

  def handle(self, *args, **options):
    expired_tickets = Ticket.objects.expired_reservations(hold_minutes=10)
    count = expired_tickets.count()
    if count == 0:
      self.stdout.write(self.style.SUCCESS('No expired holds found.'))
      return
    released_count = 0
    for ticket in expired_tickets:
        try:
            ticket.release_expired_hold()
            released_count += 1
        except Exception as e:
            self.stderr.write(f'Failed to release ticket {ticket.pk}: {str(e)}')
    self.stdout.write(self.style.SUCCESS(f'Successfully released {released_count} expired ticket holds.'))
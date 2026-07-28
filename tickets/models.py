from django.db import models
from django.conf import settings
from events.models import Event
import uuid
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from datetime import timedelta
from django.db.models import F
from django.contrib.auth import get_user_model
import io
import qrcode
from django.core.files.base import ContentFile

User = get_user_model()


class TicketQuerySet(models.QuerySet):
    def expired_reservations(self, hold_minutes=10):
        expiration_cutoff = timezone.now() - timedelta(minutes=hold_minutes)
        return self.filter(
            status=Ticket.Status.RESERVED, reserved_at__lt=expiration_cutoff
        )


class TicketType(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_tier = models.CharField(max_length=200)
    ticket_to_event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="ticket_types"
    )
    available_quantity = models.PositiveIntegerField()
    total_quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sales_start_at = models.DateTimeField()
    sales_ended_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(available_quantity__lte=models.F("total_quantity")),
                name="avalible_quantity_to_total_quantity",
            ),
            models.CheckConstraint(
                condition=models.Q(price__gte=0), name="price_gte_zero"
            ),
        ]
        ordering = ["sales_start_at", "price"]

    def reserve_ticket(self, user, hold_minutes=10):
        with transaction.atomic():
            locked_ticket_type = TicketType.objects.select_for_update().get(pk=self.pk)
            if locked_ticket_type.available_quantity <= 0:
                raise ValidationError("This ticket tier is sold out")
            now = timezone.now()
            if (
                now < locked_ticket_type.sales_start_at
                or now > locked_ticket_type.sales_ended_at
            ):
                raise ValidationError("Ticket sales are not active for this tier")
            locked_ticket_type.available_quantity = F("available_quantity") - 1
            locked_ticket_type.save(update_fields=["available_quantity"])
            ticket = Ticket.objects.create(
                ticket_type=locked_ticket_type,
                owner=user,
                status=Ticket.Status.RESERVED,
                reserved_at=now,
            )
            return ticket

    def __str__(self):
        return f"{self.ticket_tier} - {self.ticket_to_event.title}"


class Ticket(models.Model):

    class Status(models.TextChoices):
        RESERVED = "reserved", "Reserved"
        PURCHASED = "purchased", "Purchased"
        USED = "used", "Used"
        CANCELLED = "cancelled", "Cancelled"

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_type = models.ForeignKey(
        TicketType, on_delete=models.PROTECT, related_name="tickets"
    )
    owner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default="reserved")
    reserved_at = models.DateTimeField(null=True, blank=True)
    purchased_at = models.DateTimeField(null=True, blank=True)
    qr_code = models.ImageField(upload_to="ticket_qrcodes/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = TicketQuerySet.as_manager()

    class Meta:
        ordering = ["created_at"]

    def release_expired_hold(self):
        with transaction.atomic():
            updated_count = Ticket.objects.filter(
                pk=self.pk, status=Ticket.Status.RESERVED
            ).update(status=self.Status.CANCELLED)
            if updated_count > 0:
                TicketType.objects.filter(pk=self.ticket_type_id).update(
                    available_quantity=models.F("available_quantity") + 1
                )
                self.status = self.Status.CANCELLED

    def generate_qr_code(self):
        if not self.qr_code:
            qr_data = f"TICKET:{self.uuid}"
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            file_name = f"qr_{self.uuid}.png"
            self.qr_code.save(file_name, ContentFile(buffer.getvalue()), save=False)

    def __str__(self):
        return f"Ticket {self.uuid} - {self.status}"

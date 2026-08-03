from django.contrib import admin
from django.utils.html import format_html
from tickets.models import TicketType, Ticket


class TicketTypeInline(admin.TabularInline):
    model = TicketType
    extra = 1
    fields = (
        "ticket_tier",
        "price",
        "available_quantity",
        "total_quantity",
        "sales_start_at",
        "sales_ended_at",
    )
    readonly_fields = ("uuid",)


@admin.register(TicketType)
class TicketTypeAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_tier",
        "ticket_to_event",
        "price",
        "available_quantity",
        "total_quantity",
        "sales_start_at",
        "sales_ended_at",
    )
    list_filter = ("ticket_to_event", "sales_start_at", "sales_ended_at")
    search_fields = ("ticket_tier", "ticket_to_event__title")
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "short_uuid",
        "ticket_type",
        "owner",
        "status",
        "reserved_at",
        "purchased_at",
        "created_at",
    )
    list_filter = ("status", "created_at", "ticket_type__ticket_to_event")
    search_fields = (
        "uuid",
        "owner__email",
        "ticket_type__ticket_tier",
        "ticket_type__ticket_to_event__title",
    )
    readonly_fields = (
        "uuid",
        "reserved_at",
        "purchased_at",
        "created_at",
        "qr_code_preview",
    )

    fieldsets = (
        (
            "Ticket Information",
            {"fields": ("uuid", "ticket_type", "owner", "status")},
        ),
        (
            "Timestamps",
            {"fields": ("reserved_at", "purchased_at", "created_at")},
        ),
        (
            "Verification",
            {"fields": ("qr_code", "qr_code_preview")},
        ),
    )

    @admin.display(description="UUID")
    def short_uuid(self, obj):
        return str(obj.uuid)[:8] + "..."

    @admin.display(description="QR Code Preview")
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html(
                '<img src="{}" style="width: 150px; height: 150px;" />',
                obj.qr_code.url,
            )
        return "No QR code generated"
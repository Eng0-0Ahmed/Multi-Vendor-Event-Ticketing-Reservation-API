from django.contrib import admin
from .models import Event


class SoftDeletedFilter(admin.SimpleListFilter):
    title = "Soft Delete Status"
    parameter_name = "is_deleted"

    def lookups(self, request, model_admin):
        return (
            ("active", "Active (Not Deleted)"),
            ("deleted", "Soft Deleted"),
        )

    def queryset(self, request, queryset):
        if self.value() == "active":
            return queryset.filter(deleted_at__isnull=True)
        if self.value() == "deleted":
            return queryset.filter(deleted_at__isnull=False)
        return queryset


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "vendor",
        "status",
        "event_date",
        "location",
        "created_at",
        "is_deleted",
    )
    list_filter = ("status", SoftDeletedFilter, "event_date", "created_at")
    search_fields = ("title", "description", "location", "vendor__email")
    readonly_fields = ("uuid", "created_at", "updated_at", "deleted_at")

    fieldsets = (
        (
            "Event Metadata",
            {"fields": ("uuid", "vendor", "title", "status", "location")},
        ),
        (
            "Details & Schedule",
            {"fields": ("event_date", "description")},
        ),
        (
            "Audit Timestamps",
            {
                "fields": ("created_at", "updated_at", "deleted_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["soft_delete_events"]

    @admin.display(boolean=True, description="Deleted?")
    def is_deleted(self, obj):
        return obj.deleted_at is not None

    @admin.action(description="Soft delete selected events")
    def soft_delete_events(self, request, queryset):
        for event in queryset:
            event.soft_delete()
        self.message_user(request, "Selected events have been soft deleted.")

    def get_queryset(self, request):
        return Event.all_objects.get_queryset()
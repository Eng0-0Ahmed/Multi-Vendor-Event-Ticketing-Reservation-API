from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, EmailConfirmationToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "first_name",
        "family_name",
        "is_organizer",
        "is_staff",
        "is_active",
        "create_date",
    )
    list_filter = ("is_organizer", "is_staff", "is_active", "create_date")
    search_fields = ("email", "first_name", "family_name")
    ordering = ("-create_date",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal Info",
            {"fields": ("first_name", "family_name")},
        ),
        (
            "Permissions & Roles",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_organizer",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("create_date", "last_login")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "family_name",
                    "password1",
                    "password2",
                    "is_organizer",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )
    readonly_fields = ("create_date", "last_login")


@admin.register(EmailConfirmationToken)
class EmailConfirmationTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "is_expired_status")
    search_fields = ("user__email", "id")
    readonly_fields = ("id", "created_at")

    @admin.display(boolean=True, description="Expired?")
    def is_expired_status(self, obj):
        return obj.is_expired()
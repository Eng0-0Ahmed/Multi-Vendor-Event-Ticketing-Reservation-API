from rest_framework.permissions import BasePermission
from .models import User


class IsOrganizer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_organizer
        )


class IsEventOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.vendor == request.user

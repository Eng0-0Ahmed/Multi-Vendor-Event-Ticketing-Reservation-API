from rest_framework import serializers
from .models import Event
from django.utils import timezone


class EventSerializer(serializers.ModelSerializer):
    vendor_first_name = serializers.ReadOnlyField(source="vendor.first_name")
    vendor_family_name = serializers.ReadOnlyField(source="vendor.family_name")

    class Meta:
        model = Event
        fields = [
            "title",
            "vendor",
            "description",
            "location",
            "event_date",
            "created_at",
            "id",
            "vendor_first_name",
            "vendor_family_name",
            "uuid",
        ]
        read_only_fields = ["id", "vendor", "created_at"]

    def validate_event_date(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Event date cannot be in the past.")
        return value

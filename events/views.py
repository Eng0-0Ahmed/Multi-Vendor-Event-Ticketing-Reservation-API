from django.shortcuts import render
from .models import Event
from .serializers import EventSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status
from rest_framework.response import Response
from users.permissions import IsOrganizer, IsEventOwner
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
import json
from notifications.redis_client import get_redis_client


class EventListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EventSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = {
        "vendor": ["exact"],
        "title": ["icontains"],
        "event_date": ["gte", "lte", "exact"],
        "location": ["exact", "icontains"],
    }
    search_fields = [
        "vendor__first_name",
        "vendor__family_name",
        "title",
        "description",
        "location",
    ]
    ordering_fields = ["event_date", "created_at"]
    ordering = ["event_date"]

    def get_queryset(self):
        return Event.objects.filter(status="published").select_related("vendor")


class EventDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EventSerializer
    queryset = Event.objects.all().select_related("vendor")
    lookup_field = "uuid"


class EventCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsOrganizer]
    serializer_class = EventSerializer

    def perform_create(self, serializer):
        event = serializer.save(vendor=self.request.user)

        redis_client = get_redis_client()
        payload = {
            "event_type":"EVENT_CREATED_EMAIL",
            "email": self.request.user.email,
            "event_uuid": str(event.uuid),
            "event_title": event.title,
            "event_vendor": str(event.vendor),
        }
        redis_client.rpush("notifications", json.dumps(payload))


class EventEditView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated, IsOrganizer, IsEventOwner]
    serializer_class = EventSerializer
    queryset = Event.objects.all()
    lookup_field = "uuid"


class EventDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsOrganizer, IsEventOwner]
    serializer_class = EventSerializer
    queryset = Event.objects.all()

    def perform_destroy(self, instance):
        instance.soft_delete()

    lookup_field = "uuid"


class VendorEventListView(generics.ListAPIView):
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticated, IsOrganizer]

    def get_queryset(self):
        return Event.objects.filter(vendor=self.request.user).select_related("vendor")

from django.urls import path
from .views import (
    EventListView,
    EventCreateView,
    EventDetailView,
    EventEditView,
    EventDeleteView,
    VendorEventListView
)

app_name = "events"

urlpatterns = [
    path("create/", EventCreateView.as_view(), name="event-create"),
    path("", EventListView.as_view(), name="event-list"),
    path("<uuid:uuid>/", EventDetailView.as_view(), name="event-detail"),
    path("<uuid:uuid>/edit", EventEditView.as_view(), name="event-edit"),
    path("<uuid:uuid>/delete/", EventDeleteView.as_view(), name="event-delete"),
    path("vendor/",VendorEventListView.as_view(), name= "vendor-list"),
]

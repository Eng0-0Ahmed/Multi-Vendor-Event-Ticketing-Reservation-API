from django.urls import path
from .views import (
    TicketListView,
    TicketDetailView,
    MyTicketsListView,
    ReserveTicketView,
    CancelReservationView,
    StripeWebhookView,
    CreateCheckoutSessionView,
    VerifyTicketView,
)

app_name = "tickets"

urlpatterns = [
    path("types/", TicketListView.as_view(), name="ticket-type-list"),
    path("<uuid:pk>/", TicketDetailView.as_view(), name="ticket-detail"),
    path("mine/", MyTicketsListView.as_view(), name="my-ticket-list"),
    path(
        "types/<uuid:pk>/reserve/", ReserveTicketView.as_view(), name="reserve-ticket"
    ),
    path(
        "<uuid:pk>/cancel/", CancelReservationView.as_view(), name="cancel-reservation"
    ),
    path(
        "<uuid:pk>/checkout/",
        CreateCheckoutSessionView.as_view(),
        name="create-checkout-session",
    ),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
    path("verify/", VerifyTicketView.as_view(), name="ticket-verify"),
]

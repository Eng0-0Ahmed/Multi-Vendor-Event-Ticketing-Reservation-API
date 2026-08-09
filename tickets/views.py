from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import TicketType, Ticket
from .serializers import TicketSerializer, TicketTypeSerializer
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework import status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError
import stripe
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json
from .redis_client import get_redis_client
from users.permissions import IsEventOwner
stripe.api_key = settings.STRIPE_SECRET_KEY


class TicketListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TicketTypeSerializer
    queryset = TicketType.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["ticket_tier"]
    search_fields = ["ticket_tier"]
    ordering_fields = ["sales_start_at"]


class TicketDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TicketSerializer

    def get_queryset(self):
        return Ticket.objects.filter(owner=self.request.user)


class MyTicketsListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TicketSerializer

    def get_queryset(self):
        return Ticket.objects.filter(owner=self.request.user).select_related(
            "ticket_type"
        )


class ReserveTicketView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ticket_type = get_object_or_404(TicketType, pk=pk)
        try:
            ticket = ticket_type.reserve_ticket(user=request.user)
        except DjangoValidationError as e:
            raise DRFValidationError(detail=e.messages)
        return Response(TicketSerializer(ticket).data, status=status.HTTP_201_CREATED)


class CancelReservationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk, owner=request.user)
        if ticket.status != Ticket.Status.RESERVED:
            raise DRFValidationError(
                "Cannot cancel a ticket that has already been purchased or cancelled"
            )
        try:
            ticket_unreserve = ticket.release_expired_hold()
        except DjangoValidationError as e:
            raise DRFValidationError(detail=e.messages)
        return Response(
            TicketSerializer(ticket_unreserve).data, status=status.HTTP_200_OK
        )


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            ticket = Ticket.objects.get(
                uuid=pk, owner=request.user, status=Ticket.Status.RESERVED
            )
        except Ticket.DoesNotExist:
            return Response(
                {"error": "Reserved ticket not found or expired."},
                status=status.HTTP_404_NOT_FOUND,
            )
        price_in_cents = int(ticket.ticket_type.price * 100)
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"{ticket.ticket_type.ticket_to_event.title} - {ticket.ticket_type.ticket_tier}",
                        },
                        "unit_amount": price_in_cents,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            metadata={"ticket_id": str(ticket.uuid)},
            success_url="https://multi-vendor-event-ticketing-reservation-api-production.up.railway.app/api/tickets/success/",
            cancel_url="https://multi-vendor-event-ticketing-reservation-api-production.up.railway.app/cancel/",
        )
        return Response({"checkout_url": session.url}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except (ValueError, stripe.error.SignatureVerificationError):
            return HttpResponse(status=status.HTTP_400_BAD_REQUEST)
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            ticket_id = session.get("metadata", {}).get("ticket_id")
            if ticket_id:
                with transaction.atomic():
                    ticket = (
                        Ticket.objects.select_for_update()
                        .filter(uuid=ticket_id)
                        .first()
                    )
                    if ticket and ticket.status == Ticket.Status.RESERVED:
                        ticket.status = Ticket.Status.PURCHASED
                        ticket.generate_qr_code()
                        ticket.save()
                        redis_client = get_redis_client()
                        qr_url = request.build_absolute_uri(ticket.qr_code.url) if ticket.qr_code else None
                        payload = {
                            "event_type": "TICKET_PURCHASED",
                            "email": ticket.owner.email,
                            "event_id": str(ticket.ticket_type.ticket_to_event_id),
                            "ticket_uuid": str(ticket.uuid),
                            "qr_code_url": qr_url
                        }
                        
                        redis_client.rpush("notifications", json.dumps(payload))

        return HttpResponse(status=status.HTTP_200_OK)


class VerifyTicketView(APIView):
    permission_classes = [IsAuthenticated, IsEventOwner]

    def post(self, request):
        qr_data = request.data.get("qr_data", "")
        if not qr_data.startswith("TICKET:"):
            return Response(
                {"detail": "Invalid QR code format."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        raw_uuid = qr_data.replace("TICKET:", "").strip()
        try:
            ticket = Ticket.objects.get(uuid=raw_uuid)
        except (Ticket.DoesNotExist, ValueError):
            return Response(
                {"detail": "Ticket not found or invalid UUID."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if ticket.status == Ticket.Status.USED:
            return Response(
                {"detail": "Ticket has already been used! Entry denied."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if ticket.status != Ticket.Status.PURCHASED:
            return Response(
                {"detail": f"Ticket cannot be verified (Status: {ticket.status})."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ticket.status = Ticket.Status.USED
        ticket.save()
        return Response(
            {
                "detail": "Access Granted! Welcome to the event.",
                "ticket_id": str(ticket.uuid),
                "status": ticket.status,
            },
            status=status.HTTP_200_OK,
        )

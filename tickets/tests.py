from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Ticket, TicketType
from django.utils import timezone
from datetime import timedelta
from events.models import Event
import uuid
from unittest.mock import patch, MagicMock
import os
from django.conf import settings
import json

User = get_user_model()


class TicketTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testemail@gmail.com",
            first_name="test_name",
            family_name="family_test",
            password="123",
            is_active=True,
        )
        self.client.force_authenticate(user=self.user)
        self.event = Event.objects.create(
            vendor=self.user,
            title="test",
            description="test_description",
            location="anywhere",
            event_date=timezone.now() + timedelta(days=20),
        )
        self.ticket_type = TicketType.objects.create(
            ticket_tier="dummy",
            ticket_to_event=self.event,
            available_quantity=100,
            total_quantity=190,
            price=10.90,
            sales_start_at=timezone.now(),
            sales_ended_at=timezone.now() + timedelta(days=10),
        )
        self.ticket = Ticket.objects.create(
            ticket_type=self.ticket_type, owner=self.user
        )

    def test_types_list(self):
        url = reverse("tickets:ticket-type-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail(self):
        url = reverse("tickets:ticket-detail", kwargs={"pk": self.ticket.uuid})
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_my_list(self):
        url = reverse("tickets:my-ticket-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_unauthenticated(self):
        self.client.logout()
        url = reverse("tickets:ticket-detail", kwargs={"pk": self.ticket.uuid})
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_detail_other_user_ticket(self):
        user = User.objects.create_user(
            email="test_email@gmail.com",
            first_name="testname",
            family_name="familytest",
            password="123!",
            is_active=True,
        )
        self.client.force_authenticate(user=user)
        url = reverse("tickets:ticket-detail", kwargs={"pk": self.ticket.uuid})
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_fake_ticket_detail(self):
        fake_uuid = uuid.uuid4()
        url = reverse("tickets:ticket-detail", kwargs={"pk": fake_uuid})
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reserve_ticket_success(self):
        url = reverse("tickets:reserve-ticket", kwargs={"pk": self.ticket_type.uuid})
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.ticket_type.refresh_from_db()
        self.assertEqual(self.ticket_type.available_quantity, 99)

    def test_sold_out(self):
        self.ticket_type.available_quantity = 0
        self.ticket_type.save()
        url = reverse("tickets:reserve-ticket", kwargs={"pk": self.ticket_type.uuid})
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_reservation_success(self):
        self.ticket.status = Ticket.Status.RESERVED
        self.ticket.save()
        self.ticket_type.available_quantity = 99
        self.ticket_type.save()
        url = reverse("tickets:cancel-reservation", kwargs={"pk": self.ticket.uuid})
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ticket_type.refresh_from_db()
        self.assertEqual(self.ticket_type.available_quantity, 100)

    def test_release_expired_hold_method(self):
        self.ticket.status = Ticket.Status.RESERVED
        self.ticket.save()
        self.ticket_type.available_quantity = 99
        self.ticket_type.save()
        self.ticket.release_expired_hold()
        self.ticket.refresh_from_db()
        self.ticket_type.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.CANCELLED)
        self.assertEqual(self.ticket_type.available_quantity, 100)

    def test_generate_qr_code_success(self):
        self.ticket.generate_qr_code()
        self.assertTrue(bool(self.ticket.qr_code))
        self.assertTrue(self.ticket.qr_code.name.startswith("ticket_qrcodes/qr_"))
        file_path = os.path.join(settings.MEDIA_ROOT, self.ticket.qr_code.name)
        self.assertTrue(os.path.exists(file_path))
        if os.path.exists(file_path):
            os.remove(file_path)

    @patch("stripe.checkout.Session.create")
    def test_create_checkout_session_success(self, mock_stripe_create):
        mock_stripe_create.return_value = type(
            "obj", (object,), {"url": "https://checkout.stripe.com/test_url"}
        )
        url = reverse(
            "tickets:create-checkout-session", kwargs={"pk": self.ticket.uuid}
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["checkout_url"],
            "https://checkout.stripe.com/test_url",
        )
        mock_stripe_create.assert_called_once()

    @patch('tickets.views.get_redis_client')
    @patch("stripe.Webhook.construct_event")
    def test_stripe_webhook_updates_ticket_status(self, mock_construct_event, mock_get_redis_client):
        mock_redis_instance = MagicMock()
        mock_get_redis_client.return_value = mock_redis_instance
        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {"ticket_id": str(self.ticket.uuid)}}},
        }
        url = reverse("tickets:stripe-webhook")
        response = self.client.post(
            url,
            data={"dummy": "data"},
            format="json",
            HTTP_STRIPE_SIGNATURE="fake_signature",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.PURCHASED)

    @patch("stripe.Webhook.construct_event")
    @patch('tickets.views.get_redis_client')
    def test_sends_email_on_purchased(self, mock_get_redis_client, mock_construct_event):
        mock_redis_instance = MagicMock()
        mock_get_redis_client.return_value = mock_redis_instance
        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {"object": {"metadata": {"ticket_id": str(self.ticket.uuid)}}},
        }
        url = reverse("tickets:stripe-webhook")
        response = self.client.post(
            url,
            data={"dummy": "data"},
            format="json",
            HTTP_STRIPE_SIGNATURE="fake_signature",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.PURCHASED)
        self.assertTrue(bool(self.ticket.qr_code))
        mock_redis_instance.rpush.assert_called_once()
        args, kwargs = mock_redis_instance.rpush.call_args
        channel_name = args[0]
        payload = json.loads(args[1])
        self.assertEqual(channel_name, "notifications")
        self.assertEqual(payload["event_type"], "TICKET_PURCHASED")
        self.assertEqual(payload["email"], self.ticket.owner.email)
        self.assertEqual(payload["ticket_uuid"], str(self.ticket.uuid))

    def test_verify_purchased_ticket(self):
        self.ticket.status = Ticket.Status.PURCHASED
        self.ticket.save()
        url = reverse("tickets:ticket-verify")
        payload = {"qr_data": f"TICKET:{self.ticket.uuid}"}
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.USED)

    def test_verify_used_ticket(self):
        self.ticket.status = Ticket.Status.USED
        self.ticket.save()
        url = reverse("tickets:ticket-verify")
        payload = {"qr_data": f"TICKET:{self.ticket.uuid}"}
        response = self.client.post(url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been used", response.data["detail"])

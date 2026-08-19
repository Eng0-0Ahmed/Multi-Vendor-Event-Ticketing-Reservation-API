import hmac
import hashlib
import json
import os
import uuid
from unittest.mock import patch
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from events.models import Event
from tickets.models import Ticket, TicketType
from .models import WhatsAppWebhookLog
from django.contrib.auth import get_user_model

User = get_user_model()

class MetaWebhookViewTestCase(APITestCase):
    def setUp(self):
        self.url = reverse("meta-webhook")  
        self.app_secret = "test_meta_app_secret"
        self.verify_token = "test_verify_token"

        os.environ["META_APP_SECRET"] = self.app_secret
        os.environ["META_VERIFY_TOKEN"] = self.verify_token

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
            status='purchased',
            ticket_type=self.ticket_type, 
            owner=self.user,
        )
        
    def generate_signature(self, payload_bytes: bytes):
        computed_hash = hmac.new(
            key=self.app_secret.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha256,
        ).hexdigest()
        return f"sha256={computed_hash}"
    
    def build_meta_payload(self, message_body: str, msg_id: str = "wamid.12345", from_num: str = "0108897897198274827"):
        return {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "entry_id_1",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messages": [
                                    {
                                        "id": msg_id,
                                        "from": from_num,
                                        "text": {"body": message_body},
                                    }
                                ]
                            },
                        }
                    ],
                }
            ],
        }
    
    def test_webhook_verification_success(self):
        response = self.client.get(
            self.url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": self.verify_token,
                "hub.challenge": "6476129",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content.decode("utf-8"), "6476129")
    
    def test_webhook_verification_failure(self):
        response = self.client.get(
            self.url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "123456",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_post_invalid_signature_rejected(self):
        payload = self.build_meta_payload("TICKETS test")
        response = self.client.post(
            self.url,
            data=payload,
            format="json",
            HTTP_X_HUB_SIGNATURE_256="dummy",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    
    
    @patch("meta_services.views.send_whatsapp_message")
    def test_tickets_command_returns_available_tiers(self, mock_send_whatsapp):
        payload = self.build_meta_payload("TICKETS test")
        body_bytes = json.dumps(payload).encode("utf-8")
        signature = self.generate_signature(body_bytes)

        response = self.client.post(
            self.url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_whatsapp.assert_called_once()
        
        log = WhatsAppWebhookLog.objects.get(message_id="wamid.12345")
        self.assertIn("test", log.reply_sent)
        self.assertIn("dummy", log.reply_sent)
    
    @patch("meta_services.views.send_whatsapp_message")
    def test_status_command_valid_uuid(self, mock_send_whatsapp):
        payload = self.build_meta_payload(f"STATUS {self.ticket.uuid}")
        body_bytes = json.dumps(payload).encode("utf-8")
        signature = self.generate_signature(body_bytes)

        response = self.client.post(
            self.url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        log = WhatsAppWebhookLog.objects.get(message_id="wamid.12345")
        self.assertIn("PURCHASED", log.reply_sent)
    
    @patch("meta_services.views.send_whatsapp_message")
    def test_status_command_invalid_uuid(self, mock_send_whatsapp):
        payload = self.build_meta_payload("STATUS invalid-uuid-123")
        body_bytes = json.dumps(payload).encode("utf-8")
        signature = self.generate_signature(body_bytes)

        response = self.client.post(
            self.url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        log = WhatsAppWebhookLog.objects.get(message_id="wamid.12345")
        self.assertIn("Invalid UUID format", log.reply_sent)
    
    
    @patch("meta_services.views.send_whatsapp_message")
    def test_idempotency_prevents_duplicate_processing(self, mock_send_whatsapp):
        payload = self.build_meta_payload("TICKETS test", msg_id="wamid.repeat_123")
        body_bytes = json.dumps(payload).encode("utf-8")
        signature = self.generate_signature(body_bytes)
        self.client.post(
            self.url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        response_retry = self.client.post(
            self.url,
            data=body_bytes,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        self.assertEqual(response_retry.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_send_whatsapp.call_count, 1)
        self.assertEqual(WhatsAppWebhookLog.objects.filter(message_id="wamid.repeat_123").count(), 1)
    
import hmac
import hashlib
import uuid
import os
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import AllowAny
import logging
from rest_framework.response import Response
from .services.whatsapp import send_whatsapp_message
from .models import WhatsAppWebhookLog
from tickets.models import TicketType, Ticket
from events.models import Event

logger = logging.getLogger(__name__)

class MetaWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def verify_signature(self, request):
        signature_header = request.headers.get("X-Hub-Signature-256")
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        expected_hash = signature_header.split("sha256=")[1]
        app_secret = os.environ.get("META_APP_SECRET", "").encode("utf-8")
        if not app_secret:
            logger.error("META_APP_SECRET is not configured in environment variables.")
            return False
        
        computed_hash = hmac.new(
            key=app_secret,
            msg=request.body,
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(computed_hash, expected_hash)
    
    def get(self, request):
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == os.environ.get("META_VERIFY_TOKEN"):
            return HttpResponse(challenge, status=status.HTTP_200_OK)
        
        return HttpResponse("Verification failed", status=status.HTTP_403_FORBIDDEN)
    

    def post(self, request):
        if not self.verify_signature(request):
            logger.warning("Invalid X-Hub-Signature-256 header.")
            return HttpResponse("Invalid signature", status=status.HTTP_403_FORBIDDEN)
        payload = request.data

        try:
            entries = payload.get("entry", [])
            if not entries:
                return HttpResponse(status=status.HTTP_200_OK)

            entry = entries[0]
            changes = entry.get("changes", [])
            if not changes:
                return HttpResponse(status=status.HTTP_200_OK)

            value = changes[0].get("value", {})
            messages = value.get("messages", [])

            if messages:
                incoming_msg = messages[0]
                meta_message_id = incoming_msg.get("id")
                from_number = incoming_msg.get("from")
                msg_body = incoming_msg.get("text", {}).get("body", "").strip()
        
                if meta_message_id and WhatsAppWebhookLog.objects.filter(message_id=meta_message_id).exists():
                    logger.info(f"Duplicate Meta message received ({meta_message_id}). Skipping execution.")
                    return HttpResponse(status=status.HTTP_200_OK)
                
                reply_text = self.process_command(msg_body)
                send_whatsapp_message(to_phone=from_number, text=reply_text)
                
                WhatsAppWebhookLog.objects.create(
                    message_id=meta_message_id,
                    from_number=from_number,
                    message_body=msg_body,
                    reply_sent=reply_text
                )
                
                logger.info(f"Processed WhatsApp message from {from_number}")
                
        except Exception as e:
            logger.error(f"Error parsing WhatsApp payload: {e}")
        return Response({"status": "EVENT_RECEIVED"}, status=status.HTTP_200_OK)
    def process_command(self, text: str):
        if not text:
            return "Welcome to Event Support!\n\nCommands:\nTICKETS <event_name>\nSTATUS <ticket_uuid>"
        parts = text.split(maxsplit=1)
        command = parts[0].upper()
        arg = parts[1].strip() if len(parts) > 1 else ""
        if command == "TICKETS":
            if not arg:
                return "Please specify an event name"
            event = Event.objects.filter(title__icontains=arg).first()
            if not event:
                return f"No event found matching '{arg}'"
            available_tickets = TicketType.objects.select_related("ticket_to_event").filter(ticket_to_event=event, available_quantity__gt=0)[:5]
            if not available_tickets.exists():
                return f"No tickets currently available for '{event.title}'"
            
            lines = [f"Available tickets for {event.title}:"]
            
            for t in available_tickets:
                lines.append(f"- Ticket ID: {t.uuid} | Type: {t.ticket_tier} | Price: ${t.price}")
            lines.append("\nTo check status, reply: STATUS <ticket_uuid>")
            return "\n".join(lines)
        
        elif command == "STATUS":
            if not arg:
                return "Please provide Ticket UUID. Example: STATUS <ticket_uuid>"
            try:
                ticket_uuid = uuid.UUID(arg)
            except ValueError:
                return "Invalid UUID format. Please send a valid UUID string."
            ticket = Ticket.objects.filter(uuid=ticket_uuid).first()
            
            if not ticket:
                return f"No ticket found matching ID: {arg}"
            
            return f"Status: {ticket.status.upper()}"
        return (
                "Welcome to Event Support!\n\n"
                "Commands:\n"
                "TICKETS <event_name>: List available tickets for an event\n"
                "STATUS <ticket_uuid>: Check real-time ticket status"
            )
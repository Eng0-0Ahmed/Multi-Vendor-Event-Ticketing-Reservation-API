from django.db import models

class WhatsAppWebhookLog(models.Model):
    message_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    from_number = models.CharField(max_length=30)
    message_body = models.TextField()
    reply_sent = models.TextField(blank=True, null=True)
    received_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Msg from {self.from_number} at {self.received_at.strftime('%Y-%m-%d %H:%M')}"
from rest_framework import serializers
from . models import Ticket, TicketType

class TicketTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = ['uuid', 'ticket_tier', 'ticket_to_event', 'available_quantity', 'total_quantity', 'price', 'sales_start_at', 'sales_ended_at', 'created_at', 'updated_at']
        read_only_fields = ['uuid', 'total_quantity', 'created_at', 'updated_at', 'sales_start_at', '']



class TicketSerializer(serializers.ModelSerializer):
    ticket_type = TicketTypeSerializer(read_only=True)
    class Meta:
        model = Ticket
        fields = ['uuid','ticket_type', 'owner', 'status', 'reserved_at', 'purchased_at', 'created_at']
        read_only_fields = fields

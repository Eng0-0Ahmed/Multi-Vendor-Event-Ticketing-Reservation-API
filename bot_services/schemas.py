from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal

class EventSchema(BaseModel):
    uuid: UUID
    title: str
    event_date: str
    description: str
    location: str
    status: str
    vendor: str

class TicketSchema(BaseModel):
    uuid: UUID
    ticket_tier: str
    ticket_to_event: str
    available_quantity: int
    total_quantity: int
    price: Decimal
    sales_start_at: str
    sales_ended_at: str
    created_at: str
    updated_at: str
    
class AskQuestionRequest(BaseModel):
    question: str
    event_data: EventSchema
    ticket_data: list[TicketSchema] = [] 
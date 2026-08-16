from bot_services.schemas import EventSchema, TicketSchema

def format_event_context(event: EventSchema):
    formatted_text = f""" 
--- EVENT INFORMATION ---
Title: {event.title}
Date & Time: {event.event_date}
Location: {event.location}
Status: {event.status}
Description: {event.description}
Vendor: {event.vendor}
-------------------------
"""
    return formatted_text.strip()

def format_ticket_context(ticket: TicketSchema):
    formatted_text = f""" 
--- TICKET INFORMATION ---
Ticket Tier: {ticket.ticket_tier}
Available Quantity: {ticket.available_quantity}
Total Quantity: {ticket.total_quantity}
Price: {ticket.price}
Sales Period: Available from {ticket.sales_start_at} to {ticket.sales_ended_at}.
"""
    return formatted_text.strip()


def build_rag_prompt(user_query: str, matched_documents: list[str], matched_metadatas: list[dict]):
    if not matched_documents:
        context_str = "No specific event or ticket details found."
    else:
        context_str = "\n\n---\n\n".join(matched_documents)
        return f"""You are a helpful customer support assistant for an event ticketing platform.
Answer the user's question accurately using ONLY the retrieved context below.
If the information is not present in the context, state clearly that you do not have enough information to answer.

--- RETRIEVED CONTEXT ---
{context_str}

--- USER QUESTION ---
{user_query}
"""
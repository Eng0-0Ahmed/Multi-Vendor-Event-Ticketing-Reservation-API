import chromadb
from chromadb.utils import embedding_functions
from django.conf import settings
import os
from bot_services.schemas import EventSchema, TicketSchema


def get_chroma_client():
    db_path = getattr(settings, 'CHROMA_DB_PATH', os.path.join(settings.BASE_DIR, 'chroma_db'))
    return chromadb.PersistentClient(path=db_path)
    
chroma_client = get_chroma_client()


def get_vector_collection():
    default_ef = embedding_functions.DefaultEmbeddingFunction()
    return chroma_client.get_or_create_collection(
        name="app_vectors", embedding_function=default_ef
    )


def format_ticket_for_vector_db(ticket: TicketSchema, event_title: str) -> str:
    return f"Ticket Tier: {ticket.ticket_tier}\nEvent: {event_title}\nPrice: ${ticket.price}"


def upsert_ticket_to_vector_db(ticket: TicketSchema, event_title: str):
    collection = get_vector_collection()
    collection.upsert(
        ids=[str(ticket.uuid)],
        documents=[format_ticket_for_vector_db(ticket, event_title)],
        metadatas=[
            {
                "doc_type": "ticket",
                "parent_event_id": str(ticket.ticket_to_event),
                "price": float(ticket.price),
            }
        ],
    )


def format_event_for_vector_db(event: EventSchema) -> str:
    return f"Event Title: {event.title}\nLocation: {event.location}\nDescription: {event.description}"


def upsert_event_to_vector_db(event: EventSchema):
    collection = get_vector_collection()
    collection.upsert(
        ids=[str(event.uuid)],
        documents=[format_event_for_vector_db(event)],
        metadatas=[
            {
                "doc_type": "event",
                "vendor": str(event.vendor),
                "status": str(event.status),
            }
        ],
    )


def search_tickets_and_events(
    query_text: str, n_results: int = 3, doc_type: str = None
):
    collection = get_vector_collection() 
    if doc_type:
        where_clause = {
            "$and": [
                {"status": "published"},
                {"doc_type": doc_type}
            ]
        }
    else:
        where_clause = {"status": "published"}
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_clause,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return {"documents": [], "metadatas": [], "distances": []}

    matched_metadatas = results["metadatas"][0] if results.get("metadatas") else []
    matched_documents = results["documents"][0] if results.get("documents") else []
    matched_distances = results["distances"][0] if results.get("distances") else []

    return {
        "documents": matched_documents,
        "metadatas": matched_metadatas,
        "distances": matched_distances,
    }
import hashlib
from django.core.cache import cache
from django.conf import settings
from google import genai
from google.genai import types
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .services.vector_service import search_tickets_and_events
from .services.context_builder import build_rag_prompt

def get_genai_client():
    api_key = getattr(settings, 'GEMINI_API_KEY', None) or "dummy_key_for_tests"
    return genai.Client(api_key=api_key)

client = get_genai_client()

MAX_DISTANCE_THRESHOLD = 0.6


@api_view(['POST'])
@permission_classes([IsAuthenticated]) 
def chat_query_view(request):
    try:
        data = request.data
        query = data.get("query", "").strip()
        n_results = data.get("n_results", 3)

        if not query:
            return Response({"error": "Query string cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        normalized_query = query.lower()
        query_hash = hashlib.md5(normalized_query.encode("utf-8")).hexdigest()
        cache_key = f"rag_reply:{query_hash}"

        try:
            cached_response = cache.get(cache_key)
            if cached_response:
                return Response(cached_response)
        except Exception:
            pass

        search_results = search_tickets_and_events(query_text=query, n_results=n_results)
        documents = search_results.get("documents", [])
        metadatas = search_results.get("metadatas", [])
        distances = search_results.get("distances", [])

        top_distance = None
        if distances:
            first_elem = distances[0]
            if isinstance(first_elem, (list, tuple)):
                top_distance = first_elem[0] if len(first_elem) > 0 else None
            elif isinstance(first_elem, (int, float)):
                top_distance = first_elem
        if not documents or (top_distance is not None and top_distance > MAX_DISTANCE_THRESHOLD):
            fallback_payload = {
                "query": query,
                "answer": "I can only assist with published events and tickets on our platform.",
                "sources": []
            }
            try:
                cache.set(cache_key, fallback_payload, timeout=300)
            except Exception:
                pass
            return Response(fallback_payload)

        system_instruction, user_content = build_rag_prompt(
            user_query=query,
            matched_documents=documents,
            matched_metadatas=metadatas
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                )
            )
            answer_text = response.text
        except Exception:
            return Response(
                {"error": "AI service is temporarily unavailable. Please try again later."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        response_payload = {
            "query": query,
            "answer": answer_text,
            "sources": list(metadatas) if metadatas else []
        }

        try:
            cache.set(cache_key, response_payload, timeout=3600)
        except Exception:
            pass

        return Response(response_payload)
        
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

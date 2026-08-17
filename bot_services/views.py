import hashlib
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from google import genai
from google.genai import types
from django.conf import settings
from .services.vector_service import search_tickets_and_events
from .services.context_builder import build_rag_prompt

client = genai.Client(api_key=getattr(settings, 'GEMINI_API_KEY', None))

MAX_DISTANCE_THRESHOLD = 0.6

@csrf_exempt
def chat_query_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests are allowed."}, status=405)
    try:
        data = json.loads(request.body)
        query = data.get("query", "").strip()
        n_results = data.get("n_results", 3)

        if not query:
            return JsonResponse({"error": "Query string cannot be empty."}, status=400)

        normalized_query = query.lower()
        query_hash = hashlib.md5(normalized_query.encode("utf-8")).hexdigest()
        cache_key = f"rag_reply:{query_hash}"
        cached_response = cache.get(cache_key)
        
        if cached_response:
            return JsonResponse(cached_response)

        search_results = search_tickets_and_events(query_text=query, n_results=n_results)
        documents = search_results.get("documents", [])
        metadatas = search_results.get("metadatas", [])
        distances = search_results.get("distances", [])

        if not documents or (distances and distances[0] > MAX_DISTANCE_THRESHOLD):
            fallback_payload = {
                "query": query,
                "answer": "I can only assist with published events and tickets on our platform.",
                "sources": []
            }
            cache.set(cache_key, fallback_payload, timeout=300)
            return JsonResponse(fallback_payload)

        system_instruction, user_content = build_rag_prompt(
            user_query=query,
            matched_documents=documents,
            matched_metadatas=metadatas
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            )
        )

        response_payload = {
            "query": query,
            "answer": response.text,
            "sources": metadatas
        }

        cache.set(cache_key, response_payload, timeout=3600)

        return JsonResponse(response_payload)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
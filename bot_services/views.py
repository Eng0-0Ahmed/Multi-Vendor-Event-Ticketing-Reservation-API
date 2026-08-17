from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from google import genai
from google.genai import types
from django.conf import settings
from .services.vector_service import search_tickets_and_events
from .services.context_builder import build_rag_prompt

client = genai.Client(api_key=getattr(settings, 'GEMINI_API_KEY', None))


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

        search_results = search_tickets_and_events(query_text=query, n_results=n_results)
        documents = search_results.get("documents", [])
        metadatas = search_results.get("metadatas", [])

        
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
        return JsonResponse({
            "query": query,
            "answer": response.text,
            "sources": metadatas
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
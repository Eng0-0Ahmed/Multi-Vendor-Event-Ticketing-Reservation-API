from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
from django.urls import reverse

class BotServiceAPITests(APITestCase):
    def setUp(self):
        self.url = reverse("bot_services:bot-chat")
    @patch('bot_services.views.search_tickets_and_events')
    @patch('bot_services.views.client.models.generate_content')
    def test_chat_query_success(self, mock_gemini, mock_search):
        mock_search.return_value = {
            "documents": ["Ticket Tier: VIP\nEvent: Tech Summit 2026\nPrice: $100"],
            "metadatas": [{"doc_type": "ticket", "parent_event_id": "123-uuid", "price": 100.0}],
            "distances": [0.15]
        }

        class MockGeminiResponse:
            text = "Tickets for the Tech Summit 2026 VIP tier are priced at $100."
        
        mock_gemini.return_value = MockGeminiResponse()
        
        payload = {"query": "How much is the VIP ticket?", "n_results": 3}
        response = self.client.post(self.url, payload, format='json')


        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["query"], "How much is the VIP ticket?")
        self.assertIn("VIP", data["answer"])
        self.assertEqual(len(data["sources"]), 1)
    def test_chat_query_empty(self):
        payload = {"query": ""}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())

    def test_chat_invalid_method(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
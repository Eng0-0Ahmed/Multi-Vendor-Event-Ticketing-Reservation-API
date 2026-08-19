import os
import requests
import logging

logger = logging.getLogger(__name__)

def send_whatsapp_message(to_phone: str, text: str):
    token = os.environ.get("WHATSAPP_TOKEN")
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    
    url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        logger.error(f"WhatsApp API Error: {response.status_code} - {response.text}")
    return response.json()
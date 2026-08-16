from django.urls import path
from .views import chat_query_view


app_name = 'bot_services'

urlpatterns = [
 path('', chat_query_view, name= 'bot-chat')   
]
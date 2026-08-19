from django.urls import path
from .views import MetaWebhookView

urlpatterns = [
    path("webhooks/meta/", MetaWebhookView.as_view(), name="meta-webhook"),
]
from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

class Event(models.Model):
    options = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
    )
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    vendor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='users')
    title = models.CharField(max_length= 300)
    event_date = models.DateTimeField()
    description = models.TextField()
    location = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=options, default= 'published')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.status = 'cancelled'
        self.save()

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['event_date']
        constraints = [models.CheckConstraint(condition=models.Q(event_date__gt=models.F('created_at')), name='event_date_after_created_at')]
        indexes = [
            models.Index(fields=['event_date'], name='event_date_index'),
            models.Index(fields=['status', 'event_date'], name='status_event_date_index'),
            models.Index(fields=['location'], name ='location_index'),
        ]
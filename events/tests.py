from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from .models import Event
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class TestEventView(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='testemail@gmail.com', first_name= 'test_name', family_name= 'family_test', password = '123')
        self.user.is_active = True
        self.client.force_authenticate(user=self.user)
        self.user.save()
        self.event = Event.objects.create(vendor=self.user, title = 'test', description = 'test_description', location='anywhere', event_date = timezone.now()+timedelta(days=1))
        self.event2 = Event.objects.create(vendor=self.user,title='dummy',description='dummy',location='Alex',event_date=timezone.now() + timedelta(days=10))

    def test_list_event(self):
        url = reverse('events:event-list')
        response = self.client.get(url, format= 'json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['count'], 2)

    def test_event_detail(self):
        url = reverse('events:event-detail', kwargs={'uuid': self.event.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['vendor'], self.user.id)
        self.assertEqual(response.data['title'], 'test')
        self.assertEqual(response.data['description'], 'test_description')
        self.assertEqual(response.data['location'], 'anywhere')

    def test_create_event(self):
        self.user.is_organizer = True
        self.user.save()
        url = reverse('events:event-create')
        payload = {
        'title': 'New Event',
        'description': 'Event Description',
        'location': 'Cairo',
        'event_date': timezone.now() + timedelta(days=7)
        }
        response = self.client.post(url, payload, format= 'json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Event')
        self.assertEqual(response.data['description'], 'Event Description')
        self.assertEqual(response.data['location'], 'Cairo')
        self.assertEqual(response.data['vendor'], self.user.id)

    def test_edit_event(self):
        self.user.is_organizer = True
        self.user.save()
        url = reverse('events:event-edit', kwargs={'uuid': self.event.uuid})
        response = self.client.patch(url, {'location': 'Alex'}, format= 'json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['location'], 'Alex')

    def test_delete_event(self):
        self.user.is_organizer = True
        self.user.save()
        url = reverse('events:event-delete', kwargs={'uuid': self.event.uuid})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Event.objects.filter(id=self.event.id).exists())
        deleted_event = Event.all_objects.get(id=self.event.id)
        self.assertIsNotNone(deleted_event.deleted_at)
        self.assertEqual(deleted_event.status, 'cancelled')

    def test_create_event_forbidden(self):
        url = reverse('events:event-create')
        payload = {
        'title': 'New Event',
        'description': 'Event Description',
        'location': 'Cairo',
        'event_date': timezone.now() + timedelta(days=7)
        }
        response = self.client.post(url, payload, format= 'json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_edit_event_forbidden(self):
        user = User.objects.create_user(email='dummmyemail@gmail.com', first_name= 'dummy', family_name= 'dummy', password = '123dummy')
        user.is_active = True
        user.is_organizer = True
        user.save()
        self.client.force_authenticate(user=user)
        url = reverse('events:event-edit', kwargs={'uuid': self.event.uuid})
        response = self.client.patch(url, {'location': 'Alex'}, format= 'json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_event_forbidden(self):
        user = User.objects.create_user(email='dummmyemail@gmail.com', first_name= 'dummy', family_name= 'dummy', password = '123dummy')
        user.is_active = True
        user.is_organizer = True
        user.save()
        self.client.force_authenticate(user=user)
        url = reverse('events:event-delete', kwargs={'uuid': self.event.uuid})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_event_pagination(self):
        url = reverse('events:event-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['title'], 'test')

    def test_search_events_by_vendor_first_name(self):    
        url = reverse('events:event-list')
        response = self.client.get(f'{url}?vendor__first_name=test_name', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['vendor_first_name'], 'test_name')

    def test_filter_events_by_location(self):

        url = reverse('events:event-list')
        response = self.client.get(f'{url}?location__icontains=alex', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'dummy')

    def test_ordering_events_by_date(self):
        url = reverse('events:event-list')
        response = self.client.get(f'{url}?ordering=event_date', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['id'], self.event.id)
        self.assertEqual(response.data['results'][1]['id'], self.event2.id)

    def test_draft_events_not_in_public_list(self):
        Event.objects.create(
        vendor=self.user,
        title='Draft',
        description='Draft Test',
        location='dummy',
        status = 'draft',
        event_date=timezone.now() + timedelta(days=5),
        )
        url = reverse('events:event-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [event['title'] for event in response.data['results']]
        self.assertNotIn('Draft', titles)    

class TestEventSerializer(APITestCase):
    def setUp(self):
            self.user = User.objects.create_user(email='testemail@gmail.com', first_name= 'test_name', family_name= 'family_test', password = '123')
            self.user.is_active = True
            self.user.is_organizer = True
            self.client.force_authenticate(user=self.user)
            self.user.save()

    def test_create_event_past_date_invalid(self):
        url = reverse('events:event-create')
        payload = {
            'title': 'Past Event',
            'description': 'This event already happened',
            'location': 'Cairo',
            'event_date': timezone.now() - timedelta(days=1),
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('event_date', response.data)
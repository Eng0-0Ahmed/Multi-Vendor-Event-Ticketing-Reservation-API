from rest_framework.test import APITestCase
from . models import User, EmailConfirmationToken
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

User = get_user_model()


class TestLoginUser(APITestCase):
    
    def setUp(self):
        user1= User.objects.create_user(email='testemail@gmail.com', first_name= 'test_name', family_name= 'family_test', password = '123')
        user1.is_active = True
        user1.save()
    def test_user(self):
        url = reverse('users:token_obtain_pair')
        response = self.client.post(url, {'email': 'testemail@gmail.com','password': '123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)


class TestRegisterUser(APITestCase):
    def setUp(self):
        self.url = reverse('users:register')
    def test_register_user(self):
        response = self.client.post(self.url,{'email': 'newuser@gmail.com', 'password': '123password', 'first_name': 'New', 'family_name': 'User'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)


    def test_duplicate(self):
        user = User.objects.create_user(email = 'duplicate@gmail.com', first_name= 'test', family_name = 'test2', password = '123')
        user.is_active = True
        user.save()
        response = self.client.post(self.url, {'email': 'duplicate@gmail.com', 'first_name': 'try', 'family_name': 'dummy', 'password': '1234'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_missing(self):
        response = self.client.post(self.url,{'email': 'email@gmail.com', 'first_name': 'first', 'family_name': 'last'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_organizer(self):
        field={
            'email':'test@gmail.com',
            'first_name':'test',
            'family_name':'test',
            'password':'123',
            'is_organizer': True
        }
        response = self.client.post(self.url, field)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.get(email='test@gmail.com').is_organizer)
        self.assertEqual(User.objects.count(), 1)


class UserProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="profiletest@gmail.com", first_name="test", family_name="family", password="123")
        self.profile_url = reverse('users:user-profile')

    def test_get_user_profile_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
        self.assertEqual(response.data['first_name'], "test")
        self.assertEqual(response.data['family_name'], "family")

    def test_get_user_profile_unauthenticated(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_user_profile(self):
        self.client.force_authenticate(user=self.user)
        payload = {"first_name": "test_updated", "family_name": "family_name_updated"}
        
        response = self.client.patch(self.profile_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "test_updated")
        self.assertEqual(self.user.family_name, "family_name_updated")

class TestAuthentication(APITestCase):
    def setUp(self):
        user1= User.objects.create_user(email='testemail@gmail.com', first_name= 'test_name', family_name= 'family_test', password = '123')
        user1.is_active = True
        user1.save()
    def test_organizer(self):
        user = User.objects.get(email = 'testemail@gmail.com')
        user.is_organizer = True
        user.save()
        url = reverse('users:token_obtain_pair')
        response = self.client.post(url, {'email': 'testemail@gmail.com','password': '123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)




class TestEmailVerificationToken(APITestCase):
    def setUp(self):
        self.user= User.objects.create_user(email='testemail@gmail.com', first_name= 'test_name', family_name= 'family_test', password = '123')

    def test_email_verification_token(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('users:send_email_confirmation')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        token = EmailConfirmationToken.objects.filter(user=self.user).first()
        self.assertIsNotNone(token)

    def test_sending_email_verification_token(self):
        self.client.force_authenticate(user=self.user)
        token = EmailConfirmationToken.objects.create(user=self.user)
        url = reverse('users:confirm_email', kwargs={'token_id': token.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertFalse(EmailConfirmationToken.objects.filter(pk=token.id).exists())
          
          
class PasswordResetTest(APITestCase):
    def setUp(self):
        self.user= User.objects.create_user(email='testemail@gmail.com', first_name= 'test_name', family_name= 'family_test', password = '123')
        self.forgot_url = reverse('users:forgot-password')

    def test_password_request(self):
        response = self.client.post(self.forgot_url, {"email": "testemail@gmail.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

    def test_reset_password_success(self):
        self.client.post(self.forgot_url, {"email": "testemail@gmail.com"}, format="json")
        email_body = mail.outbox[0].body
        link_parts = email_body.split("/reset-password/")[1].split("/")
        uidb64, token = link_parts[0], link_parts[1]
        reset_url = reverse('users:reset-password', kwargs={'uidb64': uidb64, 'token': token})
        response = self.client.post(reset_url, {"password": "NewPassword123"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123"))


class PasswordChangeTest(APITestCase):
    def setUp(self):
        self.user= User.objects.create_user(email='testemail@gmail.com', first_name= 'test_name', family_name= 'family_test', password = '123')
        self.client.force_authenticate(user=self.user)

    def test_change_password(self):
        url=reverse('users:change-password')
        payload = {
            "old_password" : '123',
            "new_password" : "Changed123",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Changed123"))


class PermissionTesting(APITestCase):
    def setUp(self):
        self.user= User.objects.create_user(email='testemail@gmail.com', first_name= 'test_name', family_name= 'family_test', password = '123')
        self.client.force_authenticate(user=self.user)
    
    def test_updating_permission(self):
        url = reverse('users:vendor-permission')
        response = self.client.post(url,  format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_organizer)
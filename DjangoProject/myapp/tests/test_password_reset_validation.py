from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='resetuser',
            email='resetuser@example.com',
            password='pass12345',
        )

    def test_password_reset_requires_username(self):
        response = self.client.get(reverse('password_reset'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_password_reset_blocks_unknown_username(self):
        response = self.client.get(reverse('password_reset') + '?username=unknownuser')
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_password_reset_rejects_wrong_email_for_username(self):
        response = self.client.post(
            reverse('password_reset') + '?username=resetuser',
            data={
                'username': 'resetuser',
                'email': 'wrong@example.com',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter your own registered email for this username.')
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_sends_mail_for_correct_username_email(self):
        response = self.client.post(
            reverse('password_reset') + '?username=resetuser',
            data={
                'username': 'resetuser',
                'email': 'resetuser@example.com',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)

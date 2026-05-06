from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from myapp.models import Category, Department, DepartmentMember, Notification, TicketDetail
from myapp.notifications import send_notification_email


class AdminSmokeTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="smoke_admin",
            email="smoke_admin@example.com",
            password="pass12345",
        )
        self.member = User.objects.create_user(
            username="smoke_member",
            email="smoke_member@example.com",
            password="pass12345",
        )
        self.other_member = User.objects.create_user(
            username="smoke_other",
            email="smoke_other@example.com",
            password="pass12345",
        )
        self.department = Department.objects.create(
            name="Smoke IT",
            code="SMIT",
            description="Smoke department",
            color="#2563eb",
            icon="fas fa-laptop-code",
        )
        DepartmentMember.objects.create(
            user=self.member,
            department=self.department,
            role="MEMBER",
            is_active=True,
        )

    def test_category_crud_smoke(self):
        self.client.login(username="smoke_admin", password="pass12345")

        create_response = self.client.post(
            reverse("category_create"),
            data={
                "name": "Smoke Category",
                "description": "Category created in smoke test.",
                "icon": "fa-bolt",
                "color": "#123456",
                "ml_keywords": "smoke,test",
                "is_active": "on",
            },
        )
        self.assertEqual(create_response.status_code, 302)
        category = Category.objects.get(name="Smoke Category")

        edit_response = self.client.post(
            reverse("category_edit", kwargs={"pk": category.id}),
            data={
                "name": "Smoke Category Updated",
                "description": "Updated category description.",
                "icon": "fa-fire",
                "color": "#654321",
                "ml_keywords": "updated,keywords",
                "is_active": "on",
            },
        )
        self.assertEqual(edit_response.status_code, 302)
        category.refresh_from_db()
        self.assertEqual(category.name, "Smoke Category Updated")

        invalid_delete_response = self.client.get(reverse("category_delete", kwargs={"pk": category.id}), follow=True)
        self.assertEqual(invalid_delete_response.status_code, 200)
        self.assertTrue(Category.objects.filter(id=category.id).exists())

        delete_response = self.client.post(reverse("category_delete", kwargs={"pk": category.id}))
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Category.objects.filter(id=category.id).exists())

    def test_notification_actions_require_post_and_scope_to_visible_notifications(self):
        visible_ticket = TicketDetail.objects.create(
            TICKET_TITLE="Visible smoke ticket",
            TICKET_CREATED=self.other_member,
            TICKET_DUE_DATE=timezone.now().date() + timedelta(days=2),
            TICKET_DESCRIPTION="Visible notification ticket description.",
            TICKET_HOLDER="",
            TICKET_STATUS="Open",
            priority="MEDIUM",
            assigned_department=self.department,
        )
        visible_notification = Notification.objects.create(
            user=self.member,
            ticket=visible_ticket,
            notification_type="TICKET_CREATED",
            title="Visible",
            message="Visible notification",
        )
        hidden_department = Department.objects.create(
            name="Hidden Smoke",
            code="HSMK",
            description="Hidden department",
            color="#8b5cf6",
            icon="fas fa-eye-slash",
        )
        hidden_ticket = TicketDetail.objects.create(
            TICKET_TITLE="Hidden smoke ticket",
            TICKET_CREATED=self.other_member,
            TICKET_DUE_DATE=timezone.now().date() + timedelta(days=2),
            TICKET_DESCRIPTION="Hidden notification ticket description.",
            TICKET_HOLDER="",
            TICKET_STATUS="Open",
            priority="MEDIUM",
            assigned_department=hidden_department,
        )
        hidden_notification = Notification.objects.create(
            user=self.member,
            notification_type="TICKET_CREATED",
            title="Hidden",
            message="Hidden notification",
            ticket=hidden_ticket,
        )

        self.client.login(username="smoke_member", password="pass12345")

        get_mark_response = self.client.get(reverse("mark_notification_read", kwargs={"notification_id": visible_notification.id}), follow=True)
        self.assertEqual(get_mark_response.status_code, 200)
        visible_notification.refresh_from_db()
        self.assertFalse(visible_notification.is_read)

        post_mark_response = self.client.post(
            reverse("mark_notification_read", kwargs={"notification_id": visible_notification.id}),
            data={"next": reverse("notifications_list")},
        )
        self.assertEqual(post_mark_response.status_code, 302)
        visible_notification.refresh_from_db()
        self.assertTrue(visible_notification.is_read)

        get_delete_response = self.client.get(reverse("delete_notification", kwargs={"notification_id": visible_notification.id}), follow=True)
        self.assertEqual(get_delete_response.status_code, 200)
        self.assertTrue(Notification.objects.filter(id=visible_notification.id).exists())

        post_delete_response = self.client.post(
            reverse("delete_notification", kwargs={"notification_id": visible_notification.id}),
            data={"next": reverse("notifications_list")},
        )
        self.assertEqual(post_delete_response.status_code, 302)
        self.assertFalse(Notification.objects.filter(id=visible_notification.id).exists())

        Notification.objects.create(
            user=self.member,
            ticket=visible_ticket,
            notification_type="TICKET_UPDATED",
            title="Unread 1",
            message="Unread one",
        )
        Notification.objects.create(
            user=self.member,
            ticket=visible_ticket,
            notification_type="TICKET_UPDATED",
            title="Unread 2",
            message="Unread two",
        )
        mark_all_response = self.client.post(
            reverse("mark_all_read"),
            data={"next": reverse("notifications_list")},
        )
        self.assertEqual(mark_all_response.status_code, 302)
        self.assertTrue(Notification.objects.filter(id=hidden_notification.id, is_read=False).exists())
        self.assertFalse(Notification.objects.filter(user=self.member, ticket=visible_ticket, is_read=False).exists())

        delete_all_response = self.client.post(
            reverse("delete_all_notifications"),
            data={"next": reverse("notifications_list")},
        )
        self.assertEqual(delete_all_response.status_code, 302)
        self.assertTrue(Notification.objects.filter(id=hidden_notification.id).exists())
        self.assertFalse(Notification.objects.filter(user=self.member, ticket=visible_ticket).exists())

    @patch("myapp.notifications.render_to_string", return_value="<p>Notification</p>")
    @patch("myapp.notifications.send_mail", return_value=0)
    def test_notification_email_sent_flag_requires_successful_backend_send(self, mock_send_mail, _mock_render):
        notification = Notification.objects.create(
            user=self.member,
            notification_type="SYSTEM",
            title="Email accounting",
            message="Backend returned zero sends.",
        )

        result = send_notification_email(notification)

        self.assertFalse(result)
        notification.refresh_from_db()
        self.assertFalse(notification.email_sent)
        self.assertIsNone(notification.email_sent_at)
        self.assertTrue(mock_send_mail.called)

    @patch("myapp.views.get_tickets_over_time", side_effect=RuntimeError("boom"))
    def test_admin_api_returns_generic_error_without_traceback(self, _mock_helper):
        self.client.login(username="smoke_admin", password="pass12345")

        response = self.client.get(reverse("api_tickets_over_time"))

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertEqual(payload["error"], "Unable to load chart data right now.")
        self.assertNotIn("traceback", payload)

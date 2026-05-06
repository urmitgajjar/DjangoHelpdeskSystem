from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from myapp.models import Department, DepartmentMember, MyCart, Notification, TicketDetail, TicketRating
from myapp.notifications import (
    notify_ticket_accepted,
    notify_ticket_closed,
    notify_ticket_commented,
    notify_ticket_due_date_extended,
    notify_ticket_reopened,
    notify_ticket_resolved,
    notify_ticket_rated,
    notify_ticket_updated,
)
from myapp.views import _inactive_department_ticket_q


class InactiveDepartmentRuleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="inactive_admin",
            email="inactive_admin@example.com",
            password="pass12345",
        )
        self.creator = User.objects.create_user(username="inactive_creator", password="pass12345")
        self.member = User.objects.create_user(username="inactive_member", password="pass12345")
        self.other_member = User.objects.create_user(username="inactive_other", password="pass12345")

        self.active_department = Department.objects.create(
            name="Active Support",
            code="ASUP",
            description="Active support department",
            color="#2563eb",
            icon="fas fa-life-ring",
        )
        self.inactive_department = Department.objects.create(
            name="Inactive Support",
            code="ISUP",
            description="Inactive support department",
            color="#f59e0b",
            icon="fas fa-box-archive",
            is_active=False,
        )

        DepartmentMember.objects.create(
            user=self.creator,
            department=self.inactive_department,
            role="MEMBER",
            is_active=True,
        )
        DepartmentMember.objects.create(
            user=self.member,
            department=self.active_department,
            role="MEMBER",
            is_active=True,
        )
        DepartmentMember.objects.create(
            user=self.other_member,
            department=self.active_department,
            role="MEMBER",
            is_active=True,
        )

    def _create_ticket(self, department, creator=None, **kwargs):
        defaults = {
            "TICKET_TITLE": "Inactive department rule ticket",
            "TICKET_CREATED": creator or self.member,
            "TICKET_DUE_DATE": timezone.now().date() + timedelta(days=3),
            "TICKET_DESCRIPTION": "Detailed description for inactive department rule coverage.",
            "TICKET_HOLDER": "",
            "TICKET_STATUS": "Open",
            "priority": "MEDIUM",
            "assigned_department": department,
        }
        defaults.update(kwargs)
        return TicketDetail.objects.create(**defaults)

    def test_user_with_inactive_department_membership_cannot_create_ticket(self):
        self.client.login(username="inactive_creator", password="pass12345")
        before_count = TicketDetail.objects.count()

        response = self.client.post(
            reverse("ticketdetail"),
            data={
                "TICKET_TITLE": "Blocked inactive department ticket",
                "TICKET_DESCRIPTION": "This ticket should not be created while the department is inactive.",
                "TICKET_DUE_DATE": (timezone.now().date() + timedelta(days=2)).isoformat(),
                "category": "",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TicketDetail.objects.count(), before_count)
        messages = [message.message for message in response.context["messages"]]
        self.assertIn(
            "You cannot create tickets while your department is inactive. Contact an administrator.",
            messages,
        )

    @patch("myapp.views.predict_department")
    def test_ai_cannot_create_ticket_when_predicted_department_is_inactive(self, mock_predict_department):
        mock_predict_department.return_value = self.inactive_department.code
        self.client.login(username="inactive_other", password="pass12345")
        before_count = TicketDetail.objects.count()

        response = self.client.post(
            reverse("ticketdetail"),
            data={
                "TICKET_TITLE": "AI inactive department routing",
                "TICKET_DESCRIPTION": "This ticket should be blocked because AI selected an inactive department.",
                "TICKET_DUE_DATE": (timezone.now().date() + timedelta(days=2)).isoformat(),
                "category": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TicketDetail.objects.count(), before_count)
        messages = [message.message for message in response.context["messages"]]
        self.assertIn("Department is inactive.", messages)

    def test_removed_membership_from_inactive_department_does_not_hide_user_tickets(self):
        former_department = Department.objects.create(
            name="Former Desk",
            code="FDESK",
            description="Former inactive department",
            color="#64748b",
            icon="fas fa-archive",
            is_active=False,
        )
        DepartmentMember.objects.create(
            user=self.member,
            department=former_department,
            role="MEMBER",
            is_active=False,
        )
        visible_ticket = self._create_ticket(
            self.active_department,
            creator=self.member,
        )

        self.assertFalse(
            TicketDetail.objects.filter(id=visible_ticket.id).filter(_inactive_department_ticket_q()).exists()
        )

    def test_inactive_department_ticket_suppresses_all_notifications(self):
        inactive_ticket = self._create_ticket(
            self.inactive_department,
            creator=self.creator,
            assigned_to=self.creator,
            TICKET_HOLDER=self.creator.username,
            assignment_type="MANUAL",
        )
        rating = TicketRating.objects.create(
            ticket=inactive_ticket,
            rated_by=self.other_member,
            rating=5,
            feedback="Excellent resolution.",
        )

        self.assertIsNone(notify_ticket_accepted(inactive_ticket, self.other_member))
        self.assertIsNone(notify_ticket_updated(inactive_ticket, self.other_member, changes=["priority"]))
        self.assertEqual(
            notify_ticket_due_date_extended(
                inactive_ticket,
                self.other_member,
                inactive_ticket.TICKET_DUE_DATE,
                inactive_ticket.TICKET_DUE_DATE + timedelta(days=1),
            ),
            [],
        )
        self.assertIsNone(notify_ticket_closed(inactive_ticket, self.other_member))
        self.assertIsNone(notify_ticket_resolved(inactive_ticket, self.other_member))
        self.assertIsNone(notify_ticket_reopened(inactive_ticket, self.other_member))
        self.assertEqual(
            notify_ticket_commented(inactive_ticket, self.other_member, "Still blocked."),
            [],
        )
        self.assertIsNone(notify_ticket_rated(inactive_ticket, rating))
        self.assertEqual(Notification.objects.count(), 0)

    def test_admin_cannot_send_overdue_note_for_inactive_department_ticket(self):
        inactive_ticket = self._create_ticket(
            self.inactive_department,
            creator=self.creator,
            assigned_to=self.creator,
            TICKET_HOLDER=self.creator.username,
            TICKET_DUE_DATE=timezone.now().date() - timedelta(days=1),
        )

        self.client.login(username="inactive_admin", password="pass12345")
        response = self.client.post(
            reverse("send_overdue_note", kwargs={"pk": inactive_ticket.id}),
            data={"overdue_note": "Please resolve this immediately."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        messages = [message.message for message in response.context["messages"]]
        self.assertIn("Overdue notes cannot be sent for inactive-department tickets.", messages)
        self.assertEqual(Notification.objects.count(), 0)

    def test_member_cannot_reply_to_overdue_note_for_inactive_department_ticket(self):
        active_membership = DepartmentMember.objects.create(
            user=self.other_member,
            department=self.inactive_department,
            role="MEMBER",
            is_active=True,
        )
        inactive_ticket = self._create_ticket(
            self.inactive_department,
            creator=self.creator,
            assigned_to=self.other_member,
            TICKET_HOLDER=self.other_member.username,
        )

        self.client.login(username="inactive_other", password="pass12345")
        response = self.client.post(
            reverse("reply_overdue_note", kwargs={"pk": inactive_ticket.id}),
            data={"overdue_note_reply": "Working on it."},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        messages = [message.message for message in response.context["messages"]]
        self.assertIn("Overdue note replies are not allowed for inactive-department tickets.", messages)
        self.assertEqual(Notification.objects.count(), 0)
        self.assertTrue(active_membership.is_active)

    def test_admin_cannot_assign_ticket_to_inactive_department(self):
        ticket = self._create_ticket(self.active_department, creator=self.other_member)

        self.client.login(username="inactive_admin", password="pass12345")
        response = self.client.post(
            reverse("updateticket", kwargs={"pk": ticket.id}),
            data={
                "priority": ticket.priority,
                "assigned_department": str(self.inactive_department.id),
            },
        )

        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_department_id, self.active_department.id)
        self.assertIn("assigned_department", response.context["form"].errors)

    def test_inactive_department_tickets_are_hidden_from_normal_users(self):
        ticket = self._create_ticket(
            self.inactive_department,
            creator=self.creator,
            assigned_to=self.creator,
            TICKET_HOLDER=self.creator.username,
        )

        self.client.login(username="inactive_creator", password="pass12345")

        dashboard_response = self.client.get(reverse("base"))
        self.assertEqual(dashboard_response.status_code, 200)
        visible_ticket_ids = {item.id for item in dashboard_response.context["Ticketdatas"].object_list}
        self.assertNotIn(ticket.id, visible_ticket_ids)

        ticket_response = self.client.get(reverse("ticketinfo", kwargs={"pk": ticket.id}), follow=True)
        self.assertEqual(ticket_response.status_code, 200)
        redirect_chain = [url for url, _status in ticket_response.redirect_chain]
        self.assertTrue(any(reverse("base") in url for url in redirect_chain))
        messages = [message.message for message in ticket_response.context["messages"]]
        self.assertIn("You do not have permission to view this ticket.", messages)

    def test_members_are_preserved_after_department_inactive_and_reactivate(self):
        managed_department = Department.objects.create(
            name="Managed Ops",
            code="MOPS",
            description="Managed ops department",
            color="#14b8a6",
            icon="fas fa-building",
        )
        DepartmentMember.objects.create(
            user=self.member,
            department=managed_department,
            role="MEMBER",
            is_active=True,
        )
        DepartmentMember.objects.create(
            user=self.other_member,
            department=managed_department,
            role="MEMBER",
            is_active=True,
        )
        assigned_ticket = self._create_ticket(
            managed_department,
            creator=self.other_member,
            assigned_to=self.member,
            TICKET_HOLDER=self.member.username,
            assignment_type="MANUAL",
        )
        MyCart.objects.create(user=self.member, ticket=assigned_ticket)

        self.client.login(username="inactive_admin", password="pass12345")

        inactive_response = self.client.post(
            reverse("admin_delete_department", kwargs={"dept_id": managed_department.id})
        )
        self.assertEqual(inactive_response.status_code, 302)
        managed_department.refresh_from_db()
        self.assertFalse(managed_department.is_active)
        assigned_ticket.refresh_from_db()
        self.assertEqual(
            DepartmentMember.objects.filter(department=managed_department, is_active=True).count(),
            2,
        )
        self.assertIsNone(assigned_ticket.assigned_to)
        self.assertEqual(assigned_ticket.TICKET_HOLDER, "")
        self.assertFalse(MyCart.objects.filter(user=self.member, ticket=assigned_ticket).exists())

        reactivate_response = self.client.post(
            reverse("admin_reactivate_department", kwargs={"dept_id": managed_department.id})
        )
        self.assertEqual(reactivate_response.status_code, 302)
        managed_department.refresh_from_db()
        self.assertTrue(managed_department.is_active)
        assigned_ticket.refresh_from_db()
        self.assertEqual(
            DepartmentMember.objects.filter(department=managed_department, is_active=True).count(),
            2,
        )
        self.assertEqual(assigned_ticket.assigned_to_id, self.member.id)
        self.assertEqual(assigned_ticket.TICKET_HOLDER, self.member.username)
        self.assertTrue(MyCart.objects.filter(user=self.member, ticket=assigned_ticket).exists())

        self.client.logout()
        login_response = self.client.post(
            reverse("login"),
            data={
                "username": "inactive_member",
                "password": "pass12345",
                "login_as": "user",
            },
            follow=True,
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.context["user"].is_authenticated)

        dashboard_response = self.client.get(reverse("base"))
        self.assertEqual(dashboard_response.status_code, 200)
        visible_ticket_ids = {item.id for item in dashboard_response.context["Ticketdatas"].object_list}
        self.assertIn(assigned_ticket.id, visible_ticket_ids)

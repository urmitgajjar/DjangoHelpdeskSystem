from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from myapp.models import Department, DepartmentMember, MyCart, TicketDetail


class MyCartFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="memberx", password="pass12345")
        self.creator = User.objects.create_user(username="creatorx", password="pass12345")
        self.department = Department.objects.create(
            name="Support",
            code="SUP",
            description="Support team",
            color="#2563eb",
            icon="fas fa-life-ring",
        )
        DepartmentMember.objects.create(
            user=self.user, department=self.department, role="MEMBER", is_active=True
        )
        self.client.login(username="memberx", password="pass12345")

    def _create_ticket(self, **kwargs):
        defaults = {
            "TICKET_TITLE": "Ticket title for filters",
            "TICKET_CREATED": self.creator,
            "TICKET_DUE_DATE": timezone.now().date() + timedelta(days=2),
            "TICKET_DESCRIPTION": "Detailed description for ticket filtering tests.",
            "TICKET_HOLDER": self.user.username,
            "TICKET_STATUS": "Open",
            "priority": "MEDIUM",
            "assigned_department": self.department,
            "assigned_to": self.user,
        }
        defaults.update(kwargs)
        return TicketDetail.objects.create(**defaults)

    def test_urgent_filter_uses_ai_suggested_priority(self):
        urgent_ai_ticket = self._create_ticket(
            TICKET_TITLE="AI urgent ticket",
            priority="MEDIUM",
            ai_suggested_priority="URGENT",
        )
        normal_ticket = self._create_ticket(
            TICKET_TITLE="Normal ticket",
            priority="MEDIUM",
            ai_suggested_priority="MEDIUM",
        )
        MyCart.objects.get_or_create(user=self.user, ticket=urgent_ai_ticket)
        MyCart.objects.get_or_create(user=self.user, ticket=normal_ticket)

        response = self.client.get(reverse("mycart") + "?sort=urgent")
        self.assertEqual(response.status_code, 200)
        carts = list(response.context["Carts"])
        ticket_ids = {c.ticket_id for c in carts}
        self.assertIn(urgent_ai_ticket.id, ticket_ids)
        self.assertNotIn(normal_ticket.id, ticket_ids)

    def test_overdue_filter_excludes_closed_tickets(self):
        overdue_open = self._create_ticket(
            TICKET_TITLE="Overdue open ticket",
            TICKET_DUE_DATE=timezone.now().date() - timedelta(days=1),
            TICKET_STATUS="Open",
        )
        overdue_closed = self._create_ticket(
            TICKET_TITLE="Overdue closed ticket",
            TICKET_DUE_DATE=timezone.now().date() - timedelta(days=2),
            TICKET_STATUS="Closed",
        )
        MyCart.objects.get_or_create(user=self.user, ticket=overdue_open)
        MyCart.objects.get_or_create(user=self.user, ticket=overdue_closed)

        response = self.client.get(reverse("mycart") + "?sort=overdue")
        self.assertEqual(response.status_code, 200)
        carts = list(response.context["Carts"])
        ticket_ids = {c.ticket_id for c in carts}
        self.assertIn(overdue_open.id, ticket_ids)
        self.assertNotIn(overdue_closed.id, ticket_ids)

    def test_high_filter_uses_manual_or_ai_priority(self):
        high_manual = self._create_ticket(
            TICKET_TITLE="High manual ticket",
            priority="HIGH",
            ai_suggested_priority="MEDIUM",
        )
        high_ai = self._create_ticket(
            TICKET_TITLE="High AI ticket",
            priority="LOW",
            ai_suggested_priority="HIGH",
        )
        medium_ticket = self._create_ticket(
            TICKET_TITLE="Medium ticket",
            priority="MEDIUM",
            ai_suggested_priority="MEDIUM",
        )
        MyCart.objects.get_or_create(user=self.user, ticket=high_manual)
        MyCart.objects.get_or_create(user=self.user, ticket=high_ai)
        MyCart.objects.get_or_create(user=self.user, ticket=medium_ticket)

        response = self.client.get(reverse("mycart") + "?sort=high")
        self.assertEqual(response.status_code, 200)
        carts = list(response.context["Carts"])
        ticket_ids = {c.ticket_id for c in carts}
        self.assertIn(high_manual.id, ticket_ids)
        self.assertIn(high_ai.id, ticket_ids)
        self.assertNotIn(medium_ticket.id, ticket_ids)

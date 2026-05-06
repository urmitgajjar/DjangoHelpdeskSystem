from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from myapp.models import Department, DepartmentMember, TicketDetail, TicketHistory


class AnalyticsDashboardFilterTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="analytics_admin",
            email="analytics_admin@example.com",
            password="pass12345",
        )
        self.creator_it = User.objects.create_user(username="creator_it", password="pass12345")
        self.creator_hr = User.objects.create_user(username="creator_hr", password="pass12345")
        self.resolver_it = User.objects.create_user(username="resolver_it", password="pass12345")
        self.resolver_hr = User.objects.create_user(username="resolver_hr", password="pass12345")

        self.it_department = Department.objects.create(
            name="IT Analytics",
            code="ITA",
            description="IT department for analytics tests",
            color="#2563eb",
            icon="fas fa-laptop-code",
        )
        self.hr_department = Department.objects.create(
            name="HR Analytics",
            code="HRA",
            description="HR department for analytics tests",
            color="#8b5cf6",
            icon="fas fa-users",
        )
        DepartmentMember.objects.create(
            user=self.creator_it,
            department=self.it_department,
            role="MEMBER",
            is_active=True,
        )
        DepartmentMember.objects.create(
            user=self.creator_hr,
            department=self.hr_department,
            role="MEMBER",
            is_active=True,
        )
        DepartmentMember.objects.create(
            user=self.resolver_it,
            department=self.it_department,
            role="MEMBER",
            is_active=True,
        )
        DepartmentMember.objects.create(
            user=self.resolver_hr,
            department=self.hr_department,
            role="MEMBER",
            is_active=True,
        )

        self.client.login(username="analytics_admin", password="pass12345")

    def _create_ticket(self, title, creator, department):
        return TicketDetail.objects.create(
            TICKET_TITLE=title,
            TICKET_CREATED=creator,
            TICKET_DUE_DATE=timezone.now().date() + timedelta(days=2),
            TICKET_DESCRIPTION=f"{title} description",
            TICKET_HOLDER="",
            TICKET_STATUS="Open",
            priority="MEDIUM",
            assigned_department=department,
        )

    def test_top_lists_respect_explicit_department_filters(self):
        it_ticket_1 = self._create_ticket("IT creator ticket 1", self.creator_it, self.it_department)
        it_ticket_2 = self._create_ticket("IT creator ticket 2", self.creator_it, self.it_department)
        hr_ticket = self._create_ticket("HR creator ticket", self.creator_hr, self.hr_department)

        TicketHistory.objects.create(
            ticket=it_ticket_1,
            changed_by=self.resolver_it,
            action_type="CLOSED",
            description="Resolved in IT",
        )
        TicketHistory.objects.create(
            ticket=it_ticket_2,
            changed_by=self.resolver_it,
            action_type="CLOSED",
            description="Resolved in IT again",
        )
        TicketHistory.objects.create(
            ticket=hr_ticket,
            changed_by=self.resolver_hr,
            action_type="CLOSED",
            description="Resolved in HR",
        )

        response = self.client.get(
            reverse("analytics_dashboard"),
            {
                "resolver_department": self.it_department.id,
                "creator_department": self.hr_department.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["username"] for item in response.context["top_resolvers"]],
            ["resolver_it"],
        )
        self.assertEqual(
            [item["username"] for item in response.context["top_creators"]],
            ["creator_hr"],
        )

    def test_main_department_filter_is_default_for_top_lists(self):
        it_ticket = self._create_ticket("IT creator ticket", self.creator_it, self.it_department)
        hr_ticket = self._create_ticket("HR creator ticket", self.creator_hr, self.hr_department)

        TicketHistory.objects.create(
            ticket=it_ticket,
            changed_by=self.resolver_it,
            action_type="CLOSED",
            description="Resolved in IT",
        )
        TicketHistory.objects.create(
            ticket=hr_ticket,
            changed_by=self.resolver_hr,
            action_type="CLOSED",
            description="Resolved in HR",
        )

        response = self.client.get(
            reverse("analytics_dashboard"),
            {"department": self.it_department.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_department"], self.it_department)
        self.assertEqual(response.context["selected_resolver_department"], self.it_department)
        self.assertEqual(response.context["selected_creator_department"], self.it_department)
        self.assertEqual(
            [item["username"] for item in response.context["top_resolvers"]],
            ["resolver_it"],
        )
        self.assertEqual(
            [item["username"] for item in response.context["top_creators"]],
            ["creator_it"],
        )

    def test_department_filtered_top_lists_follow_user_membership_not_ticket_department(self):
        cross_ticket = self._create_ticket(
            "Cross department creator ticket",
            self.creator_it,
            self.hr_department,
        )
        TicketHistory.objects.create(
            ticket=cross_ticket,
            changed_by=self.resolver_it,
            action_type="CLOSED",
            description="Resolved by IT member on HR ticket",
        )

        response = self.client.get(
            reverse("analytics_dashboard"),
            {
                "resolver_department": self.it_department.id,
                "creator_department": self.it_department.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["username"] for item in response.context["top_resolvers"]],
            ["resolver_it"],
        )
        self.assertEqual(
            [item["username"] for item in response.context["top_creators"]],
            ["creator_it"],
        )

    def test_resolver_department_filter_uses_resolver_membership_for_resolved_status(self):
        cross_ticket = self._create_ticket(
            "Cross department resolved ticket",
            self.creator_hr,
            self.hr_department,
        )
        TicketHistory.objects.create(
            ticket=cross_ticket,
            changed_by=self.resolver_it,
            action_type="STATUS_CHANGED",
            old_value="In Progress",
            new_value="Resolved",
            description="Resolved by IT member",
        )

        response = self.client.get(
            reverse("analytics_dashboard"),
            {"resolver_department": self.it_department.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["username"] for item in response.context["top_resolvers"]],
            ["resolver_it"],
        )

    def test_top_resolvers_handles_resolved_datetime_without_silent_failure(self):
        resolved_ticket = self._create_ticket(
            "Resolved datetime ticket",
            self.creator_it,
            self.it_department,
        )
        resolved_ticket.resolved_at = timezone.now()
        resolved_ticket.TICKET_STATUS = "Resolved"
        resolved_ticket.save(update_fields=["resolved_at", "TICKET_STATUS"])

        TicketHistory.objects.create(
            ticket=resolved_ticket,
            changed_by=self.resolver_it,
            action_type="STATUS_CHANGED",
            old_value="In Progress",
            new_value="Resolved",
            description="Resolved with datetime field",
        )

        response = self.client.get(
            reverse("analytics_dashboard"),
            {"resolver_department": self.it_department.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["username"] for item in response.context["top_resolvers"]],
            ["resolver_it"],
        )

    def test_top_resolvers_excludes_ticket_creator_self_resolution(self):
        self_resolved_ticket = self._create_ticket(
            "Self resolved ticket",
            self.creator_it,
            self.it_department,
        )
        self_resolved_ticket.resolved_at = timezone.now()
        self_resolved_ticket.TICKET_STATUS = "Resolved"
        self_resolved_ticket.save(update_fields=["resolved_at", "TICKET_STATUS"])

        TicketHistory.objects.create(
            ticket=self_resolved_ticket,
            changed_by=self.creator_it,
            action_type="STATUS_CHANGED",
            old_value="In Progress",
            new_value="Resolved",
            description="Creator resolved own ticket",
        )
        TicketHistory.objects.create(
            ticket=self_resolved_ticket,
            changed_by=self.resolver_it,
            action_type="STATUS_CHANGED",
            old_value="In Progress",
            new_value="Resolved",
            description="Resolver resolved delegated ticket",
        )

        response = self.client.get(
            reverse("analytics_dashboard"),
            {"resolver_department": self.it_department.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["username"] for item in response.context["top_resolvers"]],
            ["resolver_it"],
        )

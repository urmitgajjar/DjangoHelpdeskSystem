from datetime import timedelta
from io import BytesIO

import openpyxl
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from myapp.models import Department, DepartmentMember, Notification, TicketDetail, TicketHistory


class DashboardRuntimeFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="runtime_admin",
            email="runtime_admin@example.com",
            password="pass12345",
        )
        self.member = User.objects.create_user(username="runtime_member", password="pass12345")
        self.other_member = User.objects.create_user(username="runtime_other", password="pass12345")
        self.creator_it = User.objects.create_user(username="creator_runtime_it", password="pass12345")
        self.creator_hr = User.objects.create_user(username="creator_runtime_hr", password="pass12345")
        self.resolver_it = User.objects.create_user(username="resolver_runtime_it", password="pass12345")
        self.resolver_hr = User.objects.create_user(username="resolver_runtime_hr", password="pass12345")

        self.it_department = Department.objects.create(
            name="Runtime IT",
            code="RTIT",
            description="Runtime IT department",
            color="#2563eb",
            icon="fas fa-laptop-code",
        )
        self.hr_department = Department.objects.create(
            name="Runtime HR",
            code="RTHR",
            description="Runtime HR department",
            color="#8b5cf6",
            icon="fas fa-users",
        )

        DepartmentMember.objects.create(
            user=self.member,
            department=self.it_department,
            role="MEMBER",
            is_active=True,
        )
        DepartmentMember.objects.create(
            user=self.other_member,
            department=self.hr_department,
            role="MEMBER",
            is_active=True,
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

    def _create_ticket(self, title, creator, department, **kwargs):
        defaults = {
            "TICKET_TITLE": title,
            "TICKET_CREATED": creator,
            "TICKET_DUE_DATE": timezone.now().date() + timedelta(days=2),
            "TICKET_DESCRIPTION": f"{title} description",
            "TICKET_HOLDER": "",
            "TICKET_STATUS": "Open",
            "priority": "MEDIUM",
            "assigned_department": department,
        }
        defaults.update(kwargs)
        return TicketDetail.objects.create(**defaults)

    def test_excel_export_respects_department_specific_leaderboard_filters(self):
        it_ticket = self._create_ticket("IT export ticket", self.creator_it, self.it_department)
        hr_ticket = self._create_ticket("HR export ticket", self.creator_hr, self.hr_department)

        TicketHistory.objects.create(
            ticket=it_ticket,
            changed_by=self.resolver_it,
            action_type="CLOSED",
            description="IT resolved",
        )
        TicketHistory.objects.create(
            ticket=hr_ticket,
            changed_by=self.resolver_hr,
            action_type="CLOSED",
            description="HR resolved",
        )

        self.client.login(username="runtime_admin", password="pass12345")
        response = self.client.get(
            reverse("export_analytics_excel"),
            {
                "resolver_department": self.it_department.id,
                "creator_department": self.hr_department.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        workbook = openpyxl.load_workbook(BytesIO(response.content))
        sheet = workbook["Summary"]
        self.assertEqual(sheet["A1"].value, "Helpdesk Analytics Report")

    def test_pdf_export_returns_pdf_with_filter_inputs(self):
        self._create_ticket("PDF export ticket", self.creator_it, self.it_department)

        self.client.login(username="runtime_admin", password="pass12345")
        response = self.client.get(
            reverse("export_analytics_pdf"),
            {"department": self.it_department.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_notifications_are_scoped_to_member_departments(self):
        visible_ticket = self._create_ticket("Visible notification ticket", self.creator_it, self.it_department)
        hidden_ticket = self._create_ticket("Hidden notification ticket", self.creator_hr, self.hr_department)

        visible_notification = Notification.objects.create(
            user=self.member,
            ticket=visible_ticket,
            notification_type="TICKET_UPDATED",
            title="Visible",
            message="Visible department notification",
            is_read=False,
        )
        Notification.objects.create(
            user=self.member,
            ticket=hidden_ticket,
            notification_type="TICKET_UPDATED",
            title="Hidden",
            message="Hidden department notification",
            is_read=False,
        )

        self.client.login(username="runtime_member", password="pass12345")

        list_response = self.client.get(reverse("notifications_list"))
        self.assertEqual(list_response.status_code, 200)
        notifications_page = list(list_response.context["notifications"].object_list)
        self.assertEqual([n.id for n in notifications_page], [visible_notification.id])

        count_response = self.client.get(reverse("notification_count_api"))
        self.assertEqual(count_response.status_code, 200)
        self.assertEqual(count_response.json()["count"], 1)

    def test_delete_all_notifications_only_removes_accessible_member_notifications(self):
        visible_ticket = self._create_ticket("Visible delete ticket", self.creator_it, self.it_department)
        hidden_ticket = self._create_ticket("Hidden delete ticket", self.creator_hr, self.hr_department)

        visible_notification = Notification.objects.create(
            user=self.member,
            ticket=visible_ticket,
            notification_type="TICKET_UPDATED",
            title="Visible delete",
            message="Will be deleted",
        )
        hidden_notification = Notification.objects.create(
            user=self.member,
            ticket=hidden_ticket,
            notification_type="TICKET_UPDATED",
            title="Hidden delete",
            message="Should remain",
        )

        self.client.login(username="runtime_member", password="pass12345")
        response = self.client.post(reverse("delete_all_notifications"))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Notification.objects.filter(id=visible_notification.id).exists())
        self.assertTrue(Notification.objects.filter(id=hidden_notification.id).exists())

    def test_department_analytics_renders_member_stats(self):
        resolved_ticket = self._create_ticket(
            "Resolved department ticket",
            self.member,
            self.it_department,
            assigned_to=self.member,
            TICKET_STATUS="Closed",
            TICKET_CLOSED_ON=timezone.now().date(),
        )
        TicketHistory.objects.create(
            ticket=resolved_ticket,
            changed_by=self.member,
            action_type="CLOSED",
            description="Closed by member",
        )
        self._create_ticket(
            "Active department ticket",
            self.creator_it,
            self.it_department,
            assigned_to=self.member,
            TICKET_STATUS="In Progress",
        )

        self.client.login(username="runtime_member", password="pass12345")
        response = self.client.get(
            reverse("department_analytics", kwargs={"dept_id": self.it_department.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["department"], self.it_department)
        self.assertTrue(response.context["member_stats"])
        member_stats = next(
            item for item in response.context["member_stats"]
            if item["member"].user_id == self.member.id
        )
        self.assertGreaterEqual(member_stats["tickets_created"], 1)
        self.assertGreaterEqual(member_stats["tickets_resolved"], 1)
        self.assertGreaterEqual(member_stats["active_tickets"], 1)

    def test_status_charts_page_includes_chartjs_context_data(self):
        self._create_ticket("Open chart ticket", self.creator_it, self.it_department, TICKET_STATUS="Open")
        self._create_ticket("Closed chart ticket", self.creator_hr, self.hr_department, TICKET_STATUS="Closed")

        self.client.login(username="runtime_admin", password="pass12345")
        response = self.client.get(reverse("pie_chart"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "statusDistributionChart")
        self.assertContains(response, "workflowSnapshotChart")
        self.assertIn("status_labels", response.context)
        self.assertIn("status_counts", response.context)

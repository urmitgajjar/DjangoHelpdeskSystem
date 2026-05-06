from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from myapp.models import Department, DepartmentMember, MyCart, TicketDetail, TicketHistory, Notification, TicketRating
from myapp.notifications import notify_ticket_commented, notify_ticket_rated


class RolePermissionBehaviorTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="IT Ops",
            code="ITOPS",
            description="Ops",
            color="#3b82f6",
            icon="fas fa-laptop-code",
        )
        self.creator = User.objects.create_user(username="creator", password="pass12345")
        self.member = User.objects.create_user(username="member1", password="pass12345")
        self.lead = User.objects.create_user(username="lead1", password="pass12345")
        self.manager = User.objects.create_user(username="manager1", password="pass12345")
        self.admin = User.objects.create_superuser(
            username="admin1",
            email="admin1@example.com",
            password="pass12345",
        )

        DepartmentMember.objects.create(user=self.member, department=self.department, role="MEMBER", is_active=True)
        DepartmentMember.objects.create(user=self.lead, department=self.department, role="MEMBER", is_active=True)
        DepartmentMember.objects.create(user=self.manager, department=self.department, role="MEMBER", is_active=True)

    def _create_open_ticket(self):
        return TicketDetail.objects.create(
            TICKET_TITLE="Shared printer outage in finance wing",
            TICKET_CREATED=self.creator,
            TICKET_DUE_DATE=timezone.now().date() + timedelta(days=3),
            TICKET_DESCRIPTION="Multiple users report printer queue failures and no output.",
            TICKET_HOLDER="",
            TICKET_STATUS="Open",
            priority="MEDIUM",
            assigned_department=self.department,
        )

    def test_member_can_close_department_ticket_from_queue(self):
        ticket = self._create_open_ticket()
        MyCart.objects.create(user=self.member, ticket=ticket)

        self.client.login(username="member1", password="pass12345")
        response = self.client.get(reverse("closeticket", kwargs={"pk": ticket.id}))

        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.TICKET_STATUS, "Closed")

    def test_rejected_member_cannot_close_until_auto_reassigned(self):
        ticket = self._create_open_ticket()
        MyCart.objects.create(user=self.member, ticket=ticket)
        TicketHistory.objects.create(
            ticket=ticket,
            changed_by=self.member,
            action_type="REJECTED",
            description="Ticket rejected by member1. Reason: Not available.",
        )

        self.client.login(username="member1", password="pass12345")
        response = self.client.get(reverse("closeticket", kwargs={"pk": ticket.id}))
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.TICKET_STATUS, "Open")

        TicketHistory.objects.create(
            ticket=ticket,
            changed_by=self.lead,
            action_type="ASSIGNED",
            old_value="Unassigned",
            new_value=self.member.username,
            description=f"Auto-assigned to {self.member.username} after department rejections.",
        )

        response = self.client.get(reverse("closeticket", kwargs={"pk": ticket.id}))
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.TICKET_STATUS, "Closed")

    def test_department_member_can_close_unassigned_department_ticket(self):
        ticket = self._create_open_ticket()
        MyCart.objects.create(user=self.lead, ticket=ticket)

        self.client.login(username="lead1", password="pass12345")
        response = self.client.get(reverse("closeticket", kwargs={"pk": ticket.id}))

        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.TICKET_STATUS, "Closed")

    def test_member_cannot_delete_department_ticket(self):
        ticket = self._create_open_ticket()
        self.client.login(username="member1", password="pass12345")

        response = self.client.post(reverse("deleteticket", kwargs={"pk": ticket.id}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TicketDetail.objects.filter(id=ticket.id).exists())

    def test_admin_can_delete_department_ticket(self):
        ticket = self._create_open_ticket()
        self.client.login(username="admin1", password="pass12345")

        response = self.client.post(reverse("deleteticket", kwargs={"pk": ticket.id}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TicketDetail.objects.filter(id=ticket.id).exists())

    def test_single_member_department_cannot_reject_ticket(self):
        solo_department = Department.objects.create(
            name="Solo Ops",
            code="SOLO",
            description="Single member department",
            color="#16a34a",
            icon="fas fa-user",
        )
        DepartmentMember.objects.create(
            user=self.member,
            department=solo_department,
            role="MEMBER",
            is_active=True,
        )
        ticket = TicketDetail.objects.create(
            TICKET_TITLE="Solo queue ticket",
            TICKET_CREATED=self.creator,
            TICKET_DUE_DATE=timezone.now().date() + timedelta(days=2),
            TICKET_DESCRIPTION="Only one member should not be able to reject this.",
            TICKET_HOLDER="",
            TICKET_STATUS="Open",
            priority="MEDIUM",
            assigned_department=solo_department,
        )
        MyCart.objects.create(user=self.member, ticket=ticket)

        self.client.login(username="member1", password="pass12345")
        response = self.client.post(
            reverse("removeticket", kwargs={"pk": ticket.id}),
            data={"reject_reason": "No backup member."},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(MyCart.objects.filter(user=self.member, ticket=ticket).exists())
        self.assertFalse(
            TicketHistory.objects.filter(
                ticket=ticket,
                changed_by=self.member,
                action_type="REJECTED",
            ).exists()
        )

    @patch("myapp.views.predict_department")
    @patch("myapp.views.predict_ticket_priority_with_meta")
    def test_ticket_auto_assigned_when_department_has_one_member(self, mock_predict_priority, mock_predict_department):
        solo_department = Department.objects.create(
            name="Lone Desk",
            code="LONE",
            description="One active member only",
            color="#0ea5e9",
            icon="fas fa-user-check",
        )
        mock_predict_department.return_value = "Lone Desk"
        mock_predict_priority.return_value = {
            "priority": "MEDIUM",
            "reason": "Default",
            "model": "test",
            "error": "",
        }
        DepartmentMember.objects.create(
            user=self.member,
            department=solo_department,
            role="MEMBER",
            is_active=True,
        )

        self.client.login(username="creator", password="pass12345")
        response = self.client.post(
            reverse("ticketdetail"),
            data={
                "TICKET_TITLE": "Single member assignment",
                "TICKET_DESCRIPTION": "Should auto assign to only department member.",
                "TICKET_DUE_DATE": (timezone.now().date() + timedelta(days=2)).isoformat(),
                "category": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        ticket = TicketDetail.objects.latest("id")
        self.assertEqual(ticket.assigned_department_id, solo_department.id)
        self.assertEqual(ticket.assigned_to_id, self.member.id)

    def test_admin_can_change_priority_and_department_but_not_title(self):
        other_department = Department.objects.create(
            name="HR Ops",
            code="HROPS",
            description="HR department",
            color="#8b5cf6",
            icon="fas fa-users",
        )
        ticket = self._create_open_ticket()
        original_title = ticket.TICKET_TITLE

        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("updateticket", kwargs={"pk": ticket.id}),
            data={
                "TICKET_TITLE": "Changed by admin should be ignored",
                "priority": "URGENT",
                "assigned_department": str(other_department.id),
            },
        )

        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.TICKET_TITLE, original_title)
        self.assertEqual(ticket.priority, "URGENT")
        self.assertEqual(ticket.assigned_department_id, other_department.id)

    def test_admin_can_open_ticketinfo_for_assigned_department_ticket(self):
        ticket = self._create_open_ticket()
        ticket.assigned_to = self.member
        ticket.TICKET_HOLDER = self.member.username
        ticket.assignment_type = "MANUAL"
        ticket.save(update_fields=["assigned_to", "TICKET_HOLDER", "assignment_type"])

        self.client.login(username="admin1", password="pass12345")
        response = self.client.get(reverse("ticketinfo", kwargs={"pk": ticket.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reassign Ticket")

    def test_admin_can_reassign_ticket_by_workload_to_previously_rejected_member(self):
        ticket = self._create_open_ticket()
        ticket.assigned_to = self.lead
        ticket.TICKET_HOLDER = self.lead.username
        ticket.assignment_type = "MANUAL"
        ticket.save(update_fields=["assigned_to", "TICKET_HOLDER", "assignment_type"])
        MyCart.objects.get_or_create(user=self.lead, ticket=ticket)

        TicketHistory.objects.create(
            ticket=ticket,
            changed_by=self.member,
            action_type="REJECTED",
            description="Ticket rejected by member1. Reason: Too many tickets.",
        )
        for idx in range(3):
            TicketDetail.objects.create(
                TICKET_TITLE=f"Member workload {idx}",
                TICKET_CREATED=self.creator,
                TICKET_DUE_DATE=timezone.now().date() + timedelta(days=2),
                TICKET_DESCRIPTION="Load balancing ticket.",
                TICKET_HOLDER=self.lead.username,
                TICKET_STATUS="Open",
                priority="MEDIUM",
                assigned_department=self.department,
                assigned_to=self.lead,
                assignment_type="MANUAL",
            )

        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("admin_reassign_ticket", kwargs={"pk": ticket.id}),
            data={"assigned_to": str(self.member.id)},
        )

        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_to_id, self.member.id)
        self.assertEqual(ticket.assigned_by_id, self.admin.id)
        self.assertTrue(MyCart.objects.filter(user=self.member, ticket=ticket).exists())
        self.assertFalse(MyCart.objects.filter(user=self.lead, ticket=ticket).exists())
        self.assertTrue(
            TicketHistory.objects.filter(
                ticket=ticket,
                action_type="ASSIGNED",
                new_value=self.member.username,
                description__icontains="workload review",
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.member,
                ticket=ticket,
                notification_type="TICKET_ASSIGNED",
            ).exists()
        )

        self.client.logout()
        self.client.login(username="member1", password="pass12345")
        close_response = self.client.get(reverse("closeticket", kwargs={"pk": ticket.id}))
        self.assertEqual(close_response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.TICKET_STATUS, "Closed")

    def test_admin_same_department_no_change_shows_error(self):
        ticket = self._create_open_ticket()
        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("updateticket", kwargs={"pk": ticket.id}),
            data={"assigned_department": str(self.department.id), "priority": ticket.priority},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selected department is already assigned to this ticket.")

    def test_admin_department_change_clears_old_assignee_and_moves_carts(self):
        other_department = Department.objects.create(
            name="Facilities",
            code="FAC",
            description="Facilities team",
            color="#14b8a6",
            icon="fas fa-building",
        )
        DepartmentMember.objects.create(user=self.lead, department=other_department, role="MEMBER", is_active=True)
        DepartmentMember.objects.create(user=self.manager, department=other_department, role="MEMBER", is_active=True)

        ticket = self._create_open_ticket()
        ticket.assigned_to = self.member
        ticket.TICKET_HOLDER = self.member.username
        ticket.save(update_fields=["assigned_to", "TICKET_HOLDER"])
        MyCart.objects.get_or_create(user=self.member, ticket=ticket)

        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("updateticket", kwargs={"pk": ticket.id}),
            data={"assigned_department": str(other_department.id), "priority": ticket.priority},
        )
        self.assertEqual(response.status_code, 302)

        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_department_id, other_department.id)
        self.assertIsNone(ticket.assigned_to)
        self.assertEqual(ticket.TICKET_HOLDER, "")
        self.assertFalse(MyCart.objects.filter(user=self.member, ticket=ticket).exists())
        self.assertTrue(MyCart.objects.filter(user=self.lead, ticket=ticket).exists())
        self.assertTrue(MyCart.objects.filter(user=self.manager, ticket=ticket).exists())
        self.assertTrue(Notification.objects.filter(user=self.member, ticket=ticket, notification_type="TICKET_UPDATED").exists())

    def test_admin_can_extend_due_date_for_overdue_unresolved_ticket(self):
        ticket = self._create_open_ticket()
        ticket.TICKET_STATUS = "In Progress"
        ticket.assigned_to = self.member
        old_due_date = timezone.now().date() - timedelta(days=1)
        ticket.TICKET_DUE_DATE = old_due_date
        ticket.save(update_fields=["TICKET_STATUS", "assigned_to", "TICKET_DUE_DATE"])
        new_due_date = timezone.now().date() + timedelta(days=4)

        self.client.login(username="admin1", password="pass12345")
        get_response = self.client.get(reverse("updateticket", kwargs={"pk": ticket.id}))
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, "Extend Due Date")

        post_response = self.client.post(
            reverse("updateticket", kwargs={"pk": ticket.id}),
            data={
                "priority": ticket.priority,
                "assigned_department": str(self.department.id),
                "extend_due_date": new_due_date.isoformat(),
            },
        )
        self.assertEqual(post_response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.TICKET_DUE_DATE, new_due_date)
        self.assertTrue(
            TicketHistory.objects.filter(
                ticket=ticket,
                field_name="TICKET_DUE_DATE",
                old_value=str(old_due_date),
                new_value=str(new_due_date),
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.member,
                ticket=ticket,
                notification_type="TICKET_UPDATED",
                title="Ticket due date extended",
            ).exists()
        )

    def test_admin_due_date_extension_rejects_same_or_earlier_date(self):
        ticket = self._create_open_ticket()
        ticket.TICKET_STATUS = "Open"
        old_due_date = timezone.now().date() - timedelta(days=1)
        ticket.TICKET_DUE_DATE = old_due_date
        ticket.save(update_fields=["TICKET_STATUS", "TICKET_DUE_DATE"])

        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("updateticket", kwargs={"pk": ticket.id}),
            data={
                "priority": ticket.priority,
                "assigned_department": str(self.department.id),
                "extend_due_date": ticket.TICKET_DUE_DATE.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Extended due date must be later than the current due date.")
        ticket.refresh_from_db()
        self.assertEqual(ticket.TICKET_DUE_DATE, old_due_date)

    def test_inactive_department_assignee_does_not_receive_comment_notifications(self):
        ticket = self._create_open_ticket()
        ticket.assigned_to = self.member
        ticket.TICKET_HOLDER = self.member.username
        ticket.save(update_fields=["assigned_to", "TICKET_HOLDER"])
        self.department.is_active = False
        self.department.save(update_fields=["is_active"])

        notify_ticket_commented(ticket, self.admin, "Please review the latest update.")

        self.assertFalse(
            Notification.objects.filter(
                user=self.member,
                ticket=ticket,
                notification_type="TICKET_COMMENTED",
            ).exists()
        )
        self.assertFalse(
            Notification.objects.filter(
                user=self.creator,
                ticket=ticket,
                notification_type="TICKET_COMMENTED",
            ).exists()
        )

    def test_inactive_department_assignee_does_not_receive_rating_notifications(self):
        ticket = self._create_open_ticket()
        ticket.assigned_to = self.member
        ticket.TICKET_HOLDER = self.member.username
        ticket.TICKET_STATUS = "Closed"
        ticket.save(update_fields=["assigned_to", "TICKET_HOLDER", "TICKET_STATUS"])
        self.department.is_active = False
        self.department.save(update_fields=["is_active"])

        rating = TicketRating.objects.create(
            ticket=ticket,
            rated_by=self.creator,
            rating=4,
            feedback="Resolved well.",
        )

        result = notify_ticket_rated(ticket, rating)

        self.assertIsNone(result)
        self.assertFalse(
            Notification.objects.filter(
                user=self.member,
                ticket=ticket,
                notification_type="SYSTEM",
            ).exists()
        )

    def test_admin_can_extend_due_date_before_overdue(self):
        ticket = self._create_open_ticket()
        old_due_date = ticket.TICKET_DUE_DATE
        new_due_date = old_due_date + timedelta(days=3)

        self.client.login(username="admin1", password="pass12345")
        response = self.client.post(
            reverse("updateticket", kwargs={"pk": ticket.id}),
            data={
                "priority": ticket.priority,
                "assigned_department": str(self.department.id),
                "extend_due_date": new_due_date.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.TICKET_DUE_DATE, new_due_date)

    @patch("myapp.views.predict_department")
    @patch("myapp.views.predict_ticket_priority_with_meta")
    def test_creator_cannot_submit_when_predicted_department_has_only_creator(self, mock_predict_priority, mock_predict_department):
        one_person_department = Department.objects.create(
            name="Solo Creator Dept",
            code="SCD",
            description="Only creator is present",
            color="#22c55e",
            icon="fas fa-user",
        )
        DepartmentMember.objects.create(
            user=self.creator,
            department=one_person_department,
            role="MEMBER",
            is_active=True,
        )
        mock_predict_department.return_value = "Solo Creator Dept"
        mock_predict_priority.return_value = {
            "priority": "MEDIUM",
            "reason": "Default",
            "model": "test",
            "error": "",
        }

        self.client.login(username="creator", password="pass12345")
        before_count = TicketDetail.objects.count()
        response = self.client.post(
            reverse("ticketdetail"),
            data={
                "TICKET_TITLE": "Creator only predicted department ticket",
                "TICKET_DESCRIPTION": "This should be blocked because creator is sole member.",
                "TICKET_DUE_DATE": (timezone.now().date() + timedelta(days=2)).isoformat(),
                "category": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Ticket cannot be submitted because AI routed it to your own department where you are the only active member."
        )
        self.assertEqual(TicketDetail.objects.count(), before_count)

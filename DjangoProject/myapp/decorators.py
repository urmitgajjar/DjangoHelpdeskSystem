from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import (
    DepartmentMember,
    Department,
    TicketDetail,
    get_visible_active_departments,
    get_visible_active_memberships,
)

ROLE_PERMISSION_MATRIX = {
    'MEMBER': {
        'can_assign_tickets': False,
        'can_close_tickets': False,
        'can_delete_tickets': False,
    },
    'SENIOR_MEMBER': {
        'can_assign_tickets': False,
        'can_close_tickets': True,
        'can_delete_tickets': False,
    },
    'LEAD': {
        'can_assign_tickets': True,
        'can_close_tickets': True,
        'can_delete_tickets': False,
    },
    'MANAGER': {
        'can_assign_tickets': True,
        'can_close_tickets': True,
        'can_delete_tickets': True,
    },
}


def is_admin_user(user):
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser

def user_is_department_member(user, department):
    if not user.is_authenticated or user.is_superuser:
        return False
    return DepartmentMember.objects.filter(
        user=user, department=department, is_active=True
    ).exists()


def user_department_role(user, department):
    try:
        return DepartmentMember.objects.get(
            user=user, department=department, is_active=True
        ).role
    except DepartmentMember.DoesNotExist:
        return None


def user_has_department_permission(user, department, permission_type):
    try:
        member = DepartmentMember.objects.get(
            user=user, department=department, is_active=True
        )
        role_permissions = ROLE_PERMISSION_MATRIX.get(member.role, {})
        return role_permissions.get(permission_type, False)
    except DepartmentMember.DoesNotExist:
        return False


def get_user_departments(user):
    if not user.is_authenticated or user.is_superuser:
        return Department.objects.none()
    return get_visible_active_departments(user)
    
def is_department_lead_or_higher(user, department):
    return False

def can_user_accept_ticket(user, ticket):
    if user.is_superuser:
        return False, 'Superuser cannot accept or reject tickets'

    if ticket.TICKET_STATUS != 'Open':
        return False, 'Ticket is not open for acceptance'

    if ticket.TICKET_CREATED == user:
        return False, 'You cannot accept your own ticket'

    from .models import MyCart
    if MyCart.objects.filter(ticket=ticket, user=user).exists():
        return False, 'Ticket already in your queue'

    if ticket.assigned_department:
        if not user_is_department_member(user, ticket.assigned_department):
            return False, f'This ticket belongs to {ticket.assigned_department.name} department'

    return True, 'OK'


def can_user_update_ticket(user, ticket):
    if user.is_superuser:
        return True, 'OK'
    if ticket.TICKET_CREATED == user:
        return True, 'OK'
    if ticket.assigned_to == user:
        return True, 'OK'
    if ticket.assigned_department:
        if user_has_department_permission(user, ticket.assigned_department, 'can_assign_tickets'):
            return True, 'OK'
    return False, 'You do not have permission to update this ticket'


def can_user_close_ticket(user, ticket):
    if user.is_superuser:
        return True, 'OK'
    if ticket.assigned_to == user:
        return True, 'OK'
    if ticket.assigned_department:
        if user_has_department_permission(user, ticket.assigned_department, 'can_close_tickets'):
            return True, 'OK'
    return False, 'You do not have permission to close this ticket'


def filter_tickets_by_department_access(queryset, user):
    if user.is_superuser:
        return queryset
    from django.db.models import Q
    user_departments = get_user_departments(user)
    return queryset.filter(
        Q(TICKET_CREATED=user) |
        Q(assigned_to=user) |
        Q(assigned_department__in=user_departments) |
        Q(assigned_department__isnull=True)
    ).distinct()


def get_department_statistics(department):
    tickets = TicketDetail.objects.filter(assigned_department=department)
    return {
        'total':       tickets.count(),
        'open':        tickets.filter(TICKET_STATUS='Open').count(),
        'in_progress': tickets.filter(TICKET_STATUS='In Progress').count(),
        'closed':      tickets.filter(TICKET_STATUS='Closed').count(),
        'resolved':    tickets.filter(TICKET_STATUS='Resolved').count(),
        'overdue':     tickets.filter(
            TICKET_STATUS='Open', TICKET_DUE_DATE__lt=timezone.now().date()
        ).count(),
    }

def get_user_department_context(user):
    if not user.is_authenticated:
        return {
            'user_departments':       Department.objects.none(),
            'user_department_count':  0,
            'is_department_member':   False,
            'is_department_lead':     False,
            'is_department_manager':  False,
            'department_open_tickets':  0,
            'department_count':       0,
            'department_tickets_count': 0,
        }

    user_depts = get_user_departments(user)

    memberships = get_visible_active_memberships(user)

    is_lead = False

    is_manager = False

    dept_open_tickets  = TicketDetail.objects.filter(
        assigned_department__in=user_depts, TICKET_STATUS='Open'
    ).count()

    dept_total_tickets = TicketDetail.objects.filter(
        assigned_department__in=user_depts
    ).count()

    return {
        'user_departments':       user_depts,
        'user_department_count':  user_depts.count(),
        'is_department_member':   user_depts.exists(),
        'is_department_lead':     is_lead,
        'is_department_manager':  is_manager,
        'department_open_tickets':  dept_open_tickets,
        'department_count':       user_depts.count(),
        'department_tickets_count': dept_total_tickets,
    }

def department_member_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            messages.error(
                request,
                "Superuser is not a department member."
            )
            return redirect('analytics_dashboard')                          

        if not get_user_departments(request.user).exists():
            messages.error(
                request,
                'You must be a member of a department to access this page. '
                'Please contact an administrator.',
            )
            return redirect('base')

        return view_func(request, *args, **kwargs)
    return wrapper


def ticket_department_access_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, pk, *args, **kwargs):
        ticket = get_object_or_404(TicketDetail, id=pk)
        if request.user.is_superuser:
            return view_func(request, pk, *args, **kwargs)
        if ticket.TICKET_CREATED == request.user:
            return view_func(request, pk, *args, **kwargs)
        if ticket.assigned_to == request.user:
            return view_func(request, pk, *args, **kwargs)
        if ticket.assigned_department:
            if user_is_department_member(request.user, ticket.assigned_department):
                return view_func(request, pk, *args, **kwargs)
            messages.error(
                request,
                f'Access denied. This ticket is assigned to {ticket.assigned_department.name} department.',
            )
            return redirect('base')
        return view_func(request, pk, *args, **kwargs)
    return wrapper


def department_lead_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Access denied.')
        return redirect('base')
    return wrapper


def can_assign_tickets_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, pk, *args, **kwargs):
        ticket = get_object_or_404(TicketDetail, id=pk)
        if request.user.is_superuser or ticket.TICKET_CREATED == request.user:
            return view_func(request, pk, *args, **kwargs)
        if ticket.assigned_department and user_has_department_permission(
            request.user, ticket.assigned_department, 'can_assign_tickets'
        ):
            return view_func(request, pk, *args, **kwargs)
        messages.error(request, 'Access denied. You cannot assign tickets in this department.')
        return redirect('ticketinfo', pk=pk)
    return wrapper


def can_delete_tickets_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, pk, *args, **kwargs):
        ticket = get_object_or_404(TicketDetail, id=pk)
        if request.user.is_superuser or ticket.TICKET_CREATED == request.user:
            return view_func(request, pk, *args, **kwargs)
        if ticket.assigned_department and user_has_department_permission(
            request.user, ticket.assigned_department, 'can_delete_tickets'
        ):
            return view_func(request, pk, *args, **kwargs)
        messages.error(request, 'Access denied. You cannot delete tickets in this department.')
        return redirect('ticketinfo', pk=pk)
    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if is_admin_user(request.user):
            return view_func(request, *args, **kwargs)
        messages.error(request, "Admin access required.")
        return redirect('base')
    return wrapper


class LoginRoleAuthorization:
    USER = 'user'
    ADMIN = 'admin'
    DEFAULT = USER

    MODE_CONFIG = {
        USER:  {'allow_register': True},
        ADMIN: {'allow_register': False},
    }

    @classmethod
    def normalize_mode(cls, mode):
        mode = (mode or '').strip().lower()
        return mode if mode in cls.MODE_CONFIG else cls.DEFAULT

    @classmethod
    def can_register(cls, mode):
        return cls.MODE_CONFIG[cls.normalize_mode(mode)]['allow_register']

    @classmethod
    def account_access_error(cls, mode, user):
        mode = cls.normalize_mode(mode)
        if mode == cls.ADMIN:
            if not user.is_superuser:
                return "This login page is for administrators only. Please use the user login page."
        else:
            if user.is_superuser:
                return "Superuser accounts must log in via the Admin login page."
            has_inactive_department_membership = DepartmentMember.objects.filter(
                user=user,
                is_active=True,
                department__is_active=False,
            ).exists()
            has_active_department_membership = get_visible_active_memberships(user).exists()
            if has_inactive_department_membership and not has_active_department_membership:
                return "Department is not active."
        return ""

    @classmethod
    def success_redirect(cls, mode, user, dashboard_url_fn):
        return dashboard_url_fn(user)

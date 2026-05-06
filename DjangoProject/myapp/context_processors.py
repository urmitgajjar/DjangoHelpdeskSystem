from myapp.models import (
    Notification,
    TicketDetail,
    Department,
    DepartmentMember,
    MyCart,
    get_visible_active_memberships,
)
from django.db.models import Q
from django.urls import reverse
from .decorators import get_user_department_context


def ticket_count(request):
    if not request.user.is_authenticated:
        return {
            'ticket_count':              0,
            'unread_notifications':    0,
            'my_tickets_count':          0,
            'my_open_tickets':           0,
            'my_cart_count':           0,
            'user_role':               None,
            'is_agent':                False,
            'is_admin':                False,
            'user_departments':        Department.objects.none(),
            'user_department_count':   0,
            'department_open_tickets':   0,
            'is_department_member':    False,
            'recent_notifications':    [],
            'department_count':        0,
            'department_tickets_count':  0,
            'primary_department':      None,
            'dashboard_url':           '/',
        }

    user = request.user

                                                                                
                                                                
    is_admin = user.is_superuser
    is_agent = is_admin
    user_role = 'ADMIN' if is_admin else 'USER'

                                                                                
    memberships = get_visible_active_memberships(user).order_by('department__name')

    department_ids = [m.department_id for m in memberships]

                                                                             
    primary_membership = memberships.first()
    primary_department = primary_membership.department if primary_membership else None

                                                                                
    dashboard_url = reverse('base')

    my_department_url = reverse('department_members') if memberships.exists() else None

                                                                                
                                                       
    inbox_count = TicketDetail.objects.filter(
        ~Q(TICKET_STATUS__in=['Closed', 'Resolved'])
    ).filter(
        Q(assigned_department_id__in=department_ids) | Q(assigned_to=user)
    ).distinct().count()

    my_tickets_count = TicketDetail.objects.filter(TICKET_CREATED=user).count()
    my_open_tickets  = TicketDetail.objects.filter(
        TICKET_CREATED=user, TICKET_STATUS='Open'
    ).count()

    my_cart_count = MyCart.objects.filter(user=user).count()

                                                                                
    notifications_qs = Notification.objects.filter(
        user=user
    ).select_related('ticket', 'ticket__assigned_department')

    if not is_admin:
        notifications_qs = notifications_qs.filter(
            Q(ticket__isnull=True) |
            Q(ticket__assigned_department_id__in=department_ids) |
            Q(ticket__TICKET_CREATED=user) |
            Q(ticket__assigned_to=user) |
            Q(ticket__TICKET_CLOSED=user)
        )

    unread_notifications = notifications_qs.filter(is_read=False).count()
    recent_notifications = notifications_qs.order_by('-created_at')[:5]

                                                                                
    dept_context = get_user_department_context(user)

    return {
                
        'ticket_count':            inbox_count,
        'unread_notifications':  unread_notifications,
        'my_tickets_count':        my_tickets_count,
        'my_open_tickets':         my_open_tickets,
        'my_cart_count':         my_cart_count,

              
        'user_role':             user_role,
        'is_agent':              is_agent,
        'is_admin':              is_admin,

                    
        'dashboard_url':         dashboard_url,
        'my_department_url':     my_department_url,
        'primary_department':    primary_department,
        'user_departments':      [m.department for m in memberships],

                       
        'recent_notifications':  recent_notifications,

                                                                               
        **dept_context,
    }

from datetime import date, datetime, time, timedelta

from django.db.models import Count, F, Q
from django.utils import timezone

from .models import TicketDetail, Department, DepartmentMember, ActivityLog, TicketHistory
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


def _coerce_to_dates(start_value, end_value):
    if isinstance(start_value, datetime):
        start_value = start_value.date()
    if isinstance(end_value, datetime):
        end_value = end_value.date()
    return start_value, end_value


def _coerce_to_aware_datetimes(start_value, end_value):
    if isinstance(start_value, date) and not isinstance(start_value, datetime):
        start_value = datetime.combine(start_value, time.min)
    if isinstance(end_value, date) and not isinstance(end_value, datetime):
        end_value = datetime.combine(end_value, time.max)
    if timezone.is_naive(start_value):
        start_value = timezone.make_aware(start_value, timezone.get_current_timezone())
    if timezone.is_naive(end_value):
        end_value = timezone.make_aware(end_value, timezone.get_current_timezone())
    return start_value, end_value

def get_date_range(range_type='30_days'):
    today = date.today()

    if range_type == '7_days':
        return today - timedelta(days=7), today
    if range_type == '30_days':
        return today - timedelta(days=30), today
    if range_type == '90_days':
        return today - timedelta(days=90), today
    if range_type == 'this_month':
        return today.replace(day=1), today
    if range_type == 'last_month':
        last = today.replace(day=1) - timedelta(days=1)
        return last.replace(day=1), last
    if range_type == 'this_year':
        return today.replace(month=1, day=1), today
    return today - timedelta(days=30), today

def get_ticket_statistics(start_date=None, end_date=None, department=None):
    try:
        tickets = TicketDetail.objects.all()

        if start_date and end_date:
            start_date, end_date = _coerce_to_dates(start_date, end_date)
            tickets = tickets.filter(TICKET_CREATED_ON__range=[start_date, end_date])
        if department:
            tickets = tickets.filter(assigned_department=department)

        stats = {
            'total':       tickets.count(),
            'open':        tickets.filter(TICKET_STATUS='Open').count(),
            'in_progress': tickets.filter(TICKET_STATUS='In Progress').count(),
            'closed':      tickets.filter(TICKET_STATUS='Closed').count(),
            'resolved':    tickets.filter(TICKET_STATUS='Resolved').count(),
        }
        stats['by_priority'] = {
            'urgent': tickets.filter(priority='URGENT').count(),
            'high':   tickets.filter(priority='HIGH').count(),
            'medium': tickets.filter(priority='MEDIUM').count(),
            'low':    tickets.filter(priority='LOW').count(),
        }

        completed = stats['closed'] + stats['resolved']
        stats['completion_rate'] = (
            completed / stats['total'] * 100 if stats['total'] > 0 else 0
        )

        resolved_tickets = tickets.filter(
            TICKET_STATUS__in=['Closed', 'Resolved'],
            TICKET_CLOSED_ON__isnull=False,
        )
        total_days = count = 0
        for ticket in resolved_tickets:
            if ticket.TICKET_CLOSED_ON and ticket.TICKET_CREATED_ON:
                total_days += (ticket.TICKET_CLOSED_ON - ticket.TICKET_CREATED_ON).days
                count += 1
        stats['avg_resolution_hours'] = round(total_days / count * 24, 2) if count else 0

        return stats
    except Exception as e:
        logger.error(f"get_ticket_statistics error: {e}")
        return {
            'total': 0, 'open': 0, 'in_progress': 0, 'closed': 0,
            'resolved': 0, 'completion_rate': 0, 'avg_resolution_hours': 0,
            'by_priority': {'urgent': 0, 'high': 0, 'medium': 0, 'low': 0},
        }

def get_tickets_over_time(start_date=None, end_date=None, department=None):
    try:
        tickets = TicketDetail.objects.all()
        if start_date and end_date:
            start_date, end_date = _coerce_to_dates(start_date, end_date)
            tickets = tickets.filter(TICKET_CREATED_ON__range=[start_date, end_date])
        if department:
            tickets = tickets.filter(assigned_department=department)

        tickets_by_date = tickets.values('TICKET_CREATED_ON').annotate(
            count=Count('id')
        ).order_by('TICKET_CREATED_ON')
        count_map = {
            item['TICKET_CREATED_ON']: item['count']
            for item in tickets_by_date
            if item['TICKET_CREATED_ON'] is not None
        }

        if not start_date or not end_date:
            return [
                {'date': str(d), 'count': c}
                for d, c in sorted(count_map.items(), key=lambda x: x[0])
            ]

        series = []
        day = start_date
        while day <= end_date:
            series.append({
                'date': day.strftime('%b %d'),
                'count': count_map.get(day, 0),
            })
            day += timedelta(days=1)
        return series
    except Exception as e:
        logger.error(f"get_tickets_over_time error: {e}")
        return []

def get_department_statistics(start_date=None, end_date=None):
    try:
        departments = Department.objects.filter(is_active=True)
        result = []

        for dept in departments:
            tickets = TicketDetail.objects.filter(assigned_department=dept)
            if start_date and end_date:
                start_date, end_date = _coerce_to_dates(start_date, end_date)
                tickets = tickets.filter(TICKET_CREATED_ON__range=[start_date, end_date])

            total  = tickets.count()
            closed = tickets.filter(TICKET_STATUS__in=['Closed', 'Resolved']).count()
            open_t = tickets.filter(TICKET_STATUS='Open').count()

            total_days = count = 0
            for ticket in tickets.filter(TICKET_STATUS__in=['Closed','Resolved'], TICKET_CLOSED_ON__isnull=False):
                if ticket.TICKET_CLOSED_ON and ticket.TICKET_CREATED_ON:
                    total_days += (ticket.TICKET_CLOSED_ON - ticket.TICKET_CREATED_ON).days
                    count += 1

            result.append({
                'name':                  dept.name,
                'color':                 dept.color,
                'total_tickets':           total,
                'open_tickets':            open_t,
                'closed_tickets':          closed,
                'completion_rate':       round(closed / total * 100, 2) if total else 0,
                'avg_resolution_hours':  round(total_days / count * 24, 2) if count else 0,
                'members_count':         dept.get_active_members_count(),
            })

        return result
    except Exception as e:
        logger.error(f"get_department_statistics error: {e}")
        return []


def get_department_comparison():
    try:
        departments = Department.objects.filter(is_active=True)
        result = {
            'labels':      [],
            'total_tickets': [],
            'open_tickets':  [],
            'closed_tickets':[],
            'colors':      [],
        }
        for dept in departments:
            tickets = TicketDetail.objects.filter(assigned_department=dept)
            result['labels'].append(dept.name)
            result['total_tickets'].append(tickets.count())
            result['open_tickets'].append(tickets.filter(TICKET_STATUS='Open').count())
            result['closed_tickets'].append(tickets.filter(TICKET_STATUS__in=['Closed','Resolved']).count())
            result['colors'].append(dept.color)
        return result
    except Exception as e:
        logger.error(f"get_department_comparison error: {e}")
        return {'labels': [], 'total_tickets': [], 'open_tickets': [], 'closed_tickets': [], 'colors': []}

def get_top_ticket_creators(limit=10, start_date=None, end_date=None, department=None):
    try:
        tickets = TicketDetail.objects.filter(TICKET_CREATED__isnull=False)
        if start_date and end_date:
            start_date, end_date = _coerce_to_dates(start_date, end_date)
            tickets = tickets.filter(TICKET_CREATED_ON__range=[start_date, end_date])
        if department:
            creator_ids = DepartmentMember.objects.filter(
                department=department,
                is_active=True,
                user__is_active=True,
            ).values_list('user_id', flat=True)
            tickets = tickets.filter(TICKET_CREATED_id__in=creator_ids)

        top = tickets.values('TICKET_CREATED__username', 'TICKET_CREATED__id').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]

        result = []
        for item in top:
            try:
                user = User.objects.get(id=item['TICKET_CREATED__id'])
                result.append({'user': user, 'username': item['TICKET_CREATED__username'],
                               'count': item['count']})
            except User.DoesNotExist:
                pass
        return result
    except Exception as e:
        logger.error(f"get_top_ticket_creators error: {e}")
        return []


def get_top_ticket_resolvers(limit=10, start_date=None, end_date=None, department=None):
    try:
        resolver_events = TicketHistory.objects.filter(
            changed_by__isnull=False
        ).filter(
            Q(action_type='CLOSED') |
            Q(action_type='STATUS_CHANGED', new_value='Resolved')
        ).exclude(
            ticket__TICKET_CREATED_id=F('changed_by_id')
        )
        if start_date and end_date:
            start_date, end_date = _coerce_to_aware_datetimes(start_date, end_date)
            resolver_events = resolver_events.filter(changed_at__range=[start_date, end_date])
        if department:
            resolver_ids = DepartmentMember.objects.filter(
                department=department,
                is_active=True,
                user__is_active=True,
            ).values_list('user_id', flat=True)
            resolver_events = resolver_events.filter(changed_by_id__in=resolver_ids)

        top = resolver_events.values('changed_by__username', 'changed_by__id').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]

        result = []
        for item in top:
            try:
                user = User.objects.get(id=item['changed_by__id'])
                resolved_ticket_ids = resolver_events.filter(
                    changed_by=user
                ).values_list('ticket_id', flat=True).distinct()
                user_tickets = TicketDetail.objects.filter(
                    id__in=resolved_ticket_ids
                )
                total_days = count = 0
                for t in user_tickets:
                    completed_on = t.resolved_at or t.TICKET_CLOSED_ON
                    if completed_on and t.TICKET_CREATED_ON:
                        completed_date = completed_on.date() if hasattr(completed_on, 'date') else completed_on
                        total_days += (completed_date - t.TICKET_CREATED_ON).days
                        count += 1
                avg_hours = round(total_days / count * 24, 2) if count else 0
                result.append({
                    'user':                user,
                    'username':            item['changed_by__username'],
                    'count':               item['count'],
                    'avg_resolution_hours':avg_hours,
                })
            except User.DoesNotExist:
                pass
        return result
    except Exception as e:
        logger.error(f"get_top_ticket_resolvers error: {e}")
        return []

def get_priority_distribution(start_date=None, end_date=None, department=None):
    try:
        tickets = TicketDetail.objects.all()
        if start_date and end_date:
            start_date, end_date = _coerce_to_dates(start_date, end_date)
            tickets = tickets.filter(TICKET_CREATED_ON__range=[start_date, end_date])
        if department:
            tickets = tickets.filter(assigned_department=department)
        return {
            'URGENT': tickets.filter(priority='URGENT').count(),
            'HIGH':   tickets.filter(priority='HIGH').count(),
            'MEDIUM': tickets.filter(priority='MEDIUM').count(),
            'LOW':    tickets.filter(priority='LOW').count(),
        }
    except Exception as e:
        logger.error(f"get_priority_distribution error: {e}")
        return {'URGENT': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}


def get_category_distribution(start_date=None, end_date=None):
    try:
        tickets = TicketDetail.objects.filter(category__isnull=False)
        if start_date and end_date:
            start_date, end_date = _coerce_to_dates(start_date, end_date)
            tickets = tickets.filter(TICKET_CREATED_ON__range=[start_date, end_date])
        cats = tickets.values(
            'category__name', 'category__color', 'category__icon'
        ).annotate(count=Count('id')).order_by('-count')
        return [
            {'name': c['category__name'], 'count': c['count'],
             'color': c['category__color'], 'icon': c['category__icon']}
            for c in cats
        ]
    except Exception as e:
        logger.error(f"get_category_distribution error: {e}")
        return []


def get_top_active_users(limit=10, start_date=None, end_date=None):
    
    try:
        logs = ActivityLog.objects.all()
        if start_date and end_date:
            start_date, end_date = _coerce_to_dates(start_date, end_date)
            logs = logs.filter(timestamp__date__range=[start_date, end_date])

        top = logs.values('user__username', 'user__id').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]

        result = []
        for item in top:
            try:
                user = User.objects.get(id=item['user__id'])
                result.append({'user': user, 'username': item['user__username'],
                               'count': item['count']})
            except User.DoesNotExist:
                pass
        return result
    except Exception as e:
        logger.error(f"get_top_active_users error: {e}")
        return []

def prepare_export_data(start_date, end_date, department=None, resolver_department=None, creator_department=None):
    try:
        resolver_department = resolver_department or department
        creator_department = creator_department or department
        return {
            'date_range':           f"{start_date} to {end_date}",
            'generated_at':         timezone.now(),
            'statistics':           get_ticket_statistics(start_date, end_date, department),
            'department_stats':     get_department_statistics(start_date, end_date),
            'priority_distribution':get_priority_distribution(start_date, end_date, department),
            'category_distribution':get_category_distribution(start_date, end_date),
            'top_creators':         get_top_ticket_creators(10, start_date, end_date, creator_department),
            'top_resolvers':        get_top_ticket_resolvers(10, start_date, end_date, resolver_department),
        }
    except Exception as e:
        logger.error(f"prepare_export_data error: {e}")
        return {}

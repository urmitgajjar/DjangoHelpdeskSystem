from django.db import models
from django.db import connection
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_migrate
from django.dispatch import receiver


def _table_exists(table_name):
    return table_name in connection.introspection.table_names()


def get_visible_active_memberships(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return DepartmentMember.objects.none()
    return DepartmentMember.objects.filter(
        user=user,
        is_active=True,
        department__is_active=True,
    ).select_related('department')


def get_visible_active_departments(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return Department.objects.none()
    return Department.objects.filter(
        departmentmember__user=user,
        departmentmember__is_active=True,
        is_active=True,
    ).distinct()

class Department(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    code        = models.CharField(max_length=10, unique=True,
                                   help_text="Short code (e.g., IT, HR, FIN)")
    email       = models.EmailField(blank=True, help_text="Department contact email")
    is_active   = models.BooleanField(default=True)
    color       = models.CharField(max_length=7, default='#3b82f6',
                                   help_text="Hex color code for UI")
    icon        = models.CharField(max_length=50, default='fas fa-building',
                                   help_text="FontAwesome icon class")
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    null=True, related_name='departments_created')

    class Meta:
        ordering = ['name']
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

    def __str__(self):
        return self.name

    def get_active_members_count(self):
        return self.departmentmember_set.filter(is_active=True).count()

    def get_open_tickets_count(self):
        return self.department_tickets.filter(TICKET_STATUS='Open').count()

class DepartmentMember(models.Model):
    ROLE_CHOICES = [
        ('MEMBER',        'Member'),
        ('SENIOR_MEMBER', 'Senior Member'),
        ('LEAD',          'Team Lead'),
        ('MANAGER',       'Manager'),
    ]

    user                = models.ForeignKey(User, on_delete=models.CASCADE,
                                            related_name='department_memberships')
    department          = models.ForeignKey(Department, on_delete=models.CASCADE)
    role                = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER')
    is_active           = models.BooleanField(default=True)
    can_assign_tickets  = models.BooleanField(default=False)
    can_close_tickets   = models.BooleanField(default=False)
    can_delete_tickets  = models.BooleanField(default=False)
    joined_at           = models.DateTimeField(auto_now_add=True)
    added_by            = models.ForeignKey(User, on_delete=models.SET_NULL,
                                            null=True, related_name='members_added')

    class Meta:
        unique_together = ['user', 'department']
        ordering = ['department', '-role', 'user__username']
        verbose_name = 'Department Member'
        verbose_name_plural = 'Department Members'

    def __str__(self):
        return f"{self.user.username} - {self.department.name} ({self.display_role})"

    def is_manager_or_above(self):
        return self.role in ('LEAD', 'MANAGER')

    @property
    def display_role(self):
        role_labels = {
            'MEMBER':        'Member',
            'SENIOR_MEMBER': 'Senior Member',
            'LEAD':          'Team Lead',
            'MANAGER':       'Manager',
        }
        return role_labels.get(self.role, self.role.replace('_', ' ').title())

class UserProfile(models.Model):
    user  = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    Address       = models.CharField(max_length=100, blank=True)
    City          = models.CharField(max_length=100, blank=True)
    State         = models.CharField(max_length=100, blank=True)
    Profile_Image = models.ImageField(null=True, blank=True, upload_to="images/")

    DEPARTMENT_CHOICES = [
        ('FIN', 'Finance'),
        ('IT',  'IT Support'),
        ('HR',  'HR'),
        ('MGR', 'Manager'),
        ('CS',  'Customer Support'),
        ('OPS', 'Operations'),
    ]
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES,
                                  null=True, blank=True,
                                  help_text="Deprecated — use DepartmentMember")

    phone                = models.CharField(max_length=15, blank=True)
    email_notifications  = models.BooleanField(default=True)
    created_at           = models.DateTimeField(auto_now_add=True, null=True)
    updated_at           = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} profile"

    def get_departments(self):
        return get_visible_active_departments(self.user)

class Category(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon        = models.CharField(max_length=50, default='fa-folder')
    color       = models.CharField(max_length=7, default='#007bff')
    is_active   = models.BooleanField(default=True)
    ml_keywords = models.TextField(blank=True,
                                   help_text="Comma-separated keywords for ML")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class TicketDetail(models.Model):
    TICKET_TITLE       = models.CharField(max_length=100)
    TICKET_CREATED     = models.ForeignKey(User, related_name='CREATED_BY',
                                         on_delete=models.CASCADE, null=True)
    TICKET_CLOSED      = models.ForeignKey(User, related_name='CLOSED_BY',
                                         on_delete=models.CASCADE, null=True)
    TICKET_CREATED_ON  = models.DateField(auto_now_add=True, null=True)
    TICKET_DUE_DATE    = models.DateField()
    TICKET_CLOSED_ON   = models.DateTimeField(null=True)
    TICKET_DESCRIPTION = models.CharField(max_length=300)
    TICKET_HOLDER      = models.CharField(max_length=100)

    choice = [
        ('Open', 'Open'), ('In Progress', 'In Progress'),
        ('Closed', 'Closed'), ('Reopen', 'Reopen'),
        ('Resolved', 'Resolved'),
    ]
    TICKET_STATUS = models.CharField(max_length=100, choices=choice, default='Open')

    PRIORITY_CHOICES = [
        ('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('URGENT', 'Urgent'),
    ]
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES,
                                default='MEDIUM', null=True, blank=True)

    category = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='tickets')

    assigned_department = models.ForeignKey(Department, on_delete=models.SET_NULL,
                                            null=True, blank=True,
                                            related_name='department_tickets')

    DEPARTMENT_CHOICES = [
        ('HR','Human Resources'),('TECH','Technical Support'),
        ('ADMIN','Administration'),('SALES','Sales'),
        ('FINANCE','Finance'),('OTHER','Other'),
    ]
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES,
                                  null=True, blank=True,
                                  help_text="Deprecated — use assigned_department")

    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='assigned_tickets')

    ASSIGNMENT_TYPE_CHOICES = [
        ('UNASSIGNED',    'Unassigned'),
        ('AUTO_AI',       'Auto-assigned by AI'),
        ('AUTO_ML',       'Auto-assigned by ML'),
        ('MANUAL',        'Manually Assigned'),
        ('SELF_ASSIGNED', 'Self Assigned'),
    ]
    assignment_type = models.CharField(max_length=20, choices=ASSIGNMENT_TYPE_CHOICES,
                                       default='UNASSIGNED', null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assignments_made')

    updated_at  = models.DateTimeField(auto_now=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    ai_suggested_category = models.ForeignKey(Category, on_delete=models.SET_NULL,
                                               null=True, blank=True,
                                               related_name='ai_suggested_tickets')
    ai_suggested_priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES,
                                             null=True, blank=True)

    ml_predicted_department = models.ForeignKey(Department, on_delete=models.SET_NULL,
                                                null=True, blank=True,
                                                related_name='ml_predicted_tickets')
    ml_predicted_department_old = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES,
                                                   null=True, blank=True)
    ml_confidence_score  = models.FloatField(null=True, blank=True)
    is_potential_duplicate = models.BooleanField(default=False)
    similar_to           = models.ForeignKey('self', on_delete=models.SET_NULL,
                                             null=True, blank=True)
    views_count          = models.IntegerField(default=0)

    class Meta:
        ordering = ['-TICKET_CREATED_ON']
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"

    def __str__(self):
        return f"#{self.id} - {self.TICKET_TITLE}"

    @property
    def effective_priority(self):
        value = (self.ai_suggested_priority or self.priority or 'MEDIUM').strip().upper()
        valid_values = {key for key, _label in self.PRIORITY_CHOICES}
        return value if value in valid_values else 'MEDIUM'

    @property
    def effective_priority_display(self):
        labels = dict(self.PRIORITY_CHOICES)
        return labels.get(self.effective_priority, 'Medium')

    @property
    def is_overdue(self):
        if self.TICKET_STATUS in ['Closed', 'Resolved']:
            return False
        from datetime import date
        return date.today() > self.TICKET_DUE_DATE

    @property
    def days_until_due(self):
        from datetime import date
        return (self.TICKET_DUE_DATE - date.today()).days

    def can_be_accepted_by(self, user):
        if user.is_superuser:
            return True
        if self.assigned_department:
            return DepartmentMember.objects.filter(
                user=user, department=self.assigned_department, is_active=True
            ).exists()
        return True

    def assign_to_department(self, department, assigned_by=None, assignment_type='MANUAL'):
        self.assigned_department = department
        self.assignment_type     = assignment_type
        self.assigned_by         = assigned_by
        self.assigned_at         = timezone.now()
        self.save()

    def assign_to_user(self, user, assigned_by=None):
        self.assigned_to  = user
        self.assigned_by  = assigned_by
        self.assigned_at  = timezone.now()
        self.TICKET_STATUS  = 'In Progress'
        self.save()

class MyCart(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    ticket      = models.ForeignKey(TicketDetail, on_delete=models.CASCADE)
    ticket_count = models.IntegerField(default=1)
    accepted_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        unique_together = ['user', 'ticket']

    def __str__(self):
        return f"{self.user.username} - {self.ticket.TICKET_TITLE}"

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('CREATED',    'Ticket Created'),
        ('ASSIGNED',   'Ticket Assigned'),
        ('RESOLVED',   'Ticket Resolved'),
        ('DELETED',    'Ticket Deleted'),
        ('COMMENTED',  'Comment Added'),
        ('REOPENED',   'Ticket Reopened'),
        ('CLOSED',     'Ticket Closed'),
        ('UPDATED',    'Ticket Updated'),
        ('STATUS',     'Status Changed'),
        ('PRIORITY',   'Priority Changed'),
        ('SYSTEM',     'System Event'),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    ticket       = models.ForeignKey(TicketDetail, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='activity_logs')
    action     = models.CharField(max_length=20, choices=ACTION_CHOICES, default='SYSTEM')
    title      = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    old_value  = models.CharField(max_length=200, blank=True)
    new_value  = models.CharField(max_length=200, blank=True)
    timestamp  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['ticket', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.action} — {self.timestamp:%Y-%m-%d %H:%M}"

    @property
    def time_since(self):
        from django.utils.timesince import timesince
        return timesince(self.timestamp)

    def get_icon(self):
        icons = {
            'CREATED':   'fas fa-plus-circle',
            'ASSIGNED':  'fas fa-user-check',
            'RESOLVED':  'fas fa-check-circle',
            'DELETED':   'fas fa-trash-alt',
            'COMMENTED': 'fas fa-comment',
            'REOPENED':  'fas fa-redo',
            'CLOSED':    'fas fa-times-circle',
            'UPDATED':   'fas fa-edit',
            'STATUS':    'fas fa-exchange-alt',
            'PRIORITY':  'fas fa-flag',
            'SYSTEM':    'fas fa-cog',
        }
        return icons.get(self.action, 'fas fa-circle')

    def get_color(self):
        colors = {
            'CREATED':   '#4F46E5',
            'ASSIGNED':  '#0EA5E9',
            'RESOLVED':  '#10B981',
            'DELETED':   '#EF4444',
            'COMMENTED': '#6366F1',
            'REOPENED':  '#F59E0B',
            'CLOSED':    '#64748B',
            'UPDATED':   '#8B5CF6',
            'STATUS':    '#F59E0B',
            'PRIORITY':  '#DC2626',
            'SYSTEM':    '#94A3B8',
        }
        return colors.get(self.action, '#94A3B8')

class UserComment(models.Model):
    user            = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ticket            = models.ForeignKey(TicketDetail, related_name='comments',
                                        on_delete=models.CASCADE, null=True, blank=True)
    Closing_comment = models.TextField(null=True, blank=True)
    Reopen_comment  = models.TextField(null=True, blank=True)
    TextFile        = models.FileField(upload_to='accepted_attachments/', null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username if self.user else 'Unknown'}"

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('TICKET_CREATED',       'Ticket Created'),
        ('TICKET_ASSIGNED',      'Ticket Assigned'),
        ('TICKET_ACCEPTED',      'Ticket Accepted'),
        ('TICKET_UPDATED',       'Ticket Updated'),
        ('TICKET_CLOSED',        'Ticket Closed'),
        ('TICKET_RESOLVED',      'Ticket Resolved'),
        ('TICKET_REOPENED',      'Ticket Reopened'),
        ('TICKET_COMMENTED',     'Ticket Commented'),
        ('TICKET_OVERDUE',       'Ticket Overdue'),
        ('DEPARTMENT_ASSIGNED','Department Assigned'),
        ('MENTION',            'Mentioned in Ticket'),
        ('SYSTEM',             'System Notification'),
    )

    user              = models.ForeignKey(User, on_delete=models.CASCADE,
                                          related_name='notifications')
    ticket              = models.ForeignKey('TicketDetail', on_delete=models.CASCADE,
                                          null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES,
                                         default='SYSTEM')
    title             = models.CharField(max_length=200, blank=True)
    message           = models.TextField()
    extra_data        = models.JSONField(default=dict, blank=True)
    is_read           = models.BooleanField(default=False, db_index=True)
    read_at           = models.DateTimeField(null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True, db_index=True)
    email_sent        = models.BooleanField(default=False)
    email_sent_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.notification_type}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_as_unread(self):
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])

    def get_icon(self):
        icons = {
            'TICKET_CREATED':        'fas fa-plus-circle',
            'TICKET_ASSIGNED':       'fas fa-user-check',
            'TICKET_ACCEPTED':       'fas fa-hand-holding',
            'TICKET_UPDATED':        'fas fa-edit',
            'TICKET_CLOSED':         'fas fa-times-circle',
            'TICKET_RESOLVED':       'fas fa-check-circle',
            'TICKET_REOPENED':       'fas fa-redo',
            'TICKET_COMMENTED':      'fas fa-comment',
            'TICKET_OVERDUE':        'fas fa-exclamation-triangle',
            'DEPARTMENT_ASSIGNED': 'fas fa-building',
            'MENTION':             'fas fa-at',
            'SYSTEM':              'fas fa-bell',
        }
        return icons.get(self.notification_type, 'fas fa-bell')

    def get_color_class(self):
        colors = {
            'TICKET_CREATED':        'primary',
            'TICKET_ASSIGNED':       'info',
            'TICKET_ACCEPTED':       'success',
            'TICKET_UPDATED':        'warning',
            'TICKET_CLOSED':         'secondary',
            'TICKET_RESOLVED':       'success',
            'TICKET_REOPENED':       'warning',
            'TICKET_COMMENTED':      'info',
            'TICKET_OVERDUE':        'danger',
            'DEPARTMENT_ASSIGNED': 'primary',
            'MENTION':             'info',
            'SYSTEM':              'secondary',
        }
        return colors.get(self.notification_type, 'secondary')

    def get_url(self):
        if self.ticket:
            from django.urls import reverse
            return reverse('ticketinfo', kwargs={'pk': self.ticket.id})
        return '#'

    @property
    def time_since(self):
        from django.utils.timesince import timesince
        return timesince(self.created_at)

class KnowledgeBase(models.Model):
    title       = models.CharField(max_length=200)
    content     = models.TextField()
    category    = models.ForeignKey(Category, on_delete=models.CASCADE,
                                    related_name='kb_articles', null=True, blank=True)
    keywords    = models.TextField(help_text="Comma-separated keywords")
    created_by  = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    views       = models.IntegerField(default=0)
    helpful_count = models.IntegerField(default=0)
    is_published  = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Knowledge Base Article"
        verbose_name_plural = "Knowledge Base"

    def __str__(self):
        return self.title

class AIMLLog(models.Model):
    TYPE_CHOICES = [
        ('CHATBOT',    'AI Chatbot'),
        ('CATEGORY',   'Category Suggestion'),
        ('PRIORITY',   'Priority Suggestion'),
        ('DEPARTMENT', 'Department Assignment'),
        ('DUPLICATE',  'Duplicate Detection'),
    ]
    ticket        = models.ForeignKey(TicketDetail, on_delete=models.CASCADE, related_name='ai_logs')
    log_type    = models.CharField(max_length=20, choices=TYPE_CHOICES)
    input_data  = models.TextField()
    output_data = models.TextField()
    confidence  = models.FloatField(null=True, blank=True)
    was_correct = models.BooleanField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "AI/ML Log"
        verbose_name_plural = "AI/ML Logs"

    def __str__(self):
        return f"{self.log_type} - Ticket #{self.ticket.id}"

class TicketHistory(models.Model):
    ticket       = models.ForeignKey('TicketDetail', on_delete=models.CASCADE,
                                   related_name='history')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action_type = models.CharField(max_length=50, choices=[
        ('CREATED',          'Created'),
        ('UPDATED',          'Updated'),
        ('ASSIGNED',         'Assigned'),
        ('STATUS_CHANGED',   'Status Changed'),
        ('PRIORITY_CHANGED', 'Priority Changed'),
        ('COMMENTED',        'Commented'),
        ('REJECTED',         'Rejected'),
        ('DELETED',          'Deleted'),
        ('CLOSED',           'Closed'),
        ('REOPENED',         'Reopened'),
    ])
    field_name  = models.CharField(max_length=100, blank=True)
    old_value   = models.TextField(blank=True)
    new_value   = models.TextField(blank=True)
    description = models.TextField(blank=True)
    changed_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']
        verbose_name = "Ticket History"
        verbose_name_plural = "Ticket History"
        indexes = [models.Index(fields=['ticket', '-changed_at'])]

    def __str__(self):
        return f"Ticket #{self.ticket.id} - {self.action_type} by {self.changed_by}"

class CannedResponse(models.Model):
    title      = models.CharField(max_length=200)
    content    = models.TextField(help_text="Use {{ticket_id}}, {{user_name}}, {{ticket_title}}")
    category   = models.ForeignKey('Category', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='canned_responses')
    department = models.ForeignKey('Department', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='canned_responses')
    is_public  = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='canned_responses_created')
    usage_count = models.IntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-usage_count', 'title']
        verbose_name = "Canned Response"
        verbose_name_plural = "Canned Responses"

    def __str__(self):
        return self.title

    def render(self, context):
        content = self.content
        for key, value in context.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content

    def increment_usage(self):
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class TicketRating(models.Model):
    ticket    = models.OneToOneField('TicketDetail', on_delete=models.CASCADE, related_name='rating')
    rated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    rating  = models.IntegerField(choices=[
        (1,'⭐ Very Dissatisfied'),(2,'⭐⭐ Dissatisfied'),
        (3,'⭐⭐⭐ Neutral'),(4,'⭐⭐⭐⭐ Satisfied'),(5,'⭐⭐⭐⭐⭐ Very Satisfied'),
    ])
    feedback             = models.TextField(blank=True)
    resolution_quality   = models.IntegerField(choices=[(i,str(i)) for i in range(1,6)],
                                               null=True, blank=True)
    response_time_rating = models.IntegerField(choices=[(i,str(i)) for i in range(1,6)],
                                               null=True, blank=True)
    agent_helpfulness    = models.IntegerField(choices=[(i,str(i)) for i in range(1,6)],
                                               null=True, blank=True)
    rated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-rated_at']
        verbose_name = "Ticket Rating"
        verbose_name_plural = "Ticket Ratings"

    def __str__(self):
        return f"Ticket #{self.ticket.id} - {self.rating}⭐ by {self.rated_by.username}"

@receiver(post_migrate)
def create_default_departments(sender, **kwargs):
    if sender.name != 'myapp':
        return
    if not _table_exists(Department._meta.db_table):
        return
    defaults = [
        {'name':'Finance',          'code':'FIN', 'color':'#10b981','icon':'fas fa-dollar-sign',
         'description':'Handles billing, payments and financial queries',
         'email':'finance@helpdesk.com'},
        {'name':'IT Support',       'code':'IT',  'color':'#3b82f6','icon':'fas fa-laptop-code',
         'description':'Handles technical issues, software problems and network troubleshooting',
         'email':'it@helpdesk.com'},
        {'name':'HR',               'code':'HR',  'color':'#8b5cf6','icon':'fas fa-users',
         'description':'Handles employee relations, payroll and HR policies',
         'email':'hr@helpdesk.com'},
        {'name':'Manager',          'code':'MGR', 'color':'#6366f1','icon':'fas fa-user-tie',
         'description':'Handles management-level approvals and oversight',
         'email':'manager@helpdesk.com'},
        {'name':'Customer Support', 'code':'CS',  'color':'#06b6d4','icon':'fas fa-headset',
         'description':'Handles customer queries, complaints and general support',
         'email':'support@helpdesk.com'},
        {'name':'Operations',       'code':'OPS', 'color':'#f59e0b','icon':'fas fa-cogs',
         'description':'Handles facility management, logistics and procurement',
         'email':'operations@helpdesk.com'},
    ]
    created = 0
    updated = 0
    for d in defaults:
        _, was_created = Department.objects.update_or_create(
            code=d['code'],
            defaults=d,
        )
        if was_created:
            created += 1
        else:
            updated += 1
    if created or updated:
        print(f"Departments seeded: created={created}, updated={updated}")


@receiver(post_migrate)
def create_default_categories(sender, **kwargs):
    if sender.name != 'myapp':
        return
    if not _table_exists(Category._meta.db_table):
        return
    defaults = [
        {'name':'Bug Report',      'icon':'fa-bug',            'color':'#dc3545',
         'ml_keywords':'bug,error,crash,not working,broken,issue,problem,fail',
         'description':'Software bugs and technical issues that need fixing'},
        {'name':'Feature Request', 'icon':'fa-lightbulb',      'color':'#0dcaf0',
         'ml_keywords':'feature,enhancement,improvement,new,add,request,suggestion',
         'description':'New feature suggestions and enhancements'},
        {'name':'Support',         'icon':'fa-question-circle','color':'#ffc107',
         'ml_keywords':'help,support,how to,question,guide,tutorial,assistance',
         'description':'User support and help requests'},
        {'name':'Maintenance',     'icon':'fa-tools',          'color':'#6c757d',
         'ml_keywords':'maintenance,update,upgrade,patch,system,server',
         'description':'System maintenance and updates'},
        {'name':'Documentation',   'icon':'fa-book',           'color':'#0d6efd',
         'ml_keywords':'documentation,docs,readme,guide,manual,instructions',
         'description':'Documentation related tickets and improvements'},
        {'name':'Security',        'icon':'fa-shield-alt',     'color':'#d63384',
         'ml_keywords':'security,vulnerability,permission,access,password,authentication',
         'description':'Security issues, vulnerabilities and access control'},
    ]
    created = sum(
        1 for d in defaults
        if Category.objects.get_or_create(name=d['name'], defaults=d)[1]
    )
    if created:
        print(f"Created {created} categories")

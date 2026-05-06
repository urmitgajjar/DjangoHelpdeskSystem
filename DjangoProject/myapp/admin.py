from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Department, DepartmentMember,
    UserProfile, TicketDetail, MyCart, ActivityLog,
    UserComment, Category,
    Notification,
    KnowledgeBase, AIMLLog,
    TicketHistory,
    CannedResponse, TicketRating,
)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display   = ['name', 'code', 'colored_badge', 'active_members',
                      'open_tickets', 'is_active_badge', 'created_at']
    list_filter    = ['is_active', 'created_at']
    search_fields  = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by']

    fieldsets = (
        ('Basic Information', {'fields': ('name', 'code', 'description', 'email', 'is_active')}),
        ('Visual', {'fields': ('color', 'icon'), 'classes': ('collapse',)}),
        ('Metadata', {'fields': ('created_by', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    def colored_badge(self, obj):
        return format_html(
            '<span style="background:{};color:white;padding:4px 12px;border-radius:6px;font-weight:600;">'
            '<i class="{}"></i> {}</span>',
            obj.color, obj.icon, obj.name
        )
    colored_badge.short_description = 'Badge'

    def active_members(self, obj):
        return format_html('<span style="color:#10b981;font-weight:600;">{} members</span>',
                           obj.get_active_members_count())
    active_members.short_description = 'Members'

    def open_tickets(self, obj):
        count = obj.get_open_tickets_count()
        color = '#ef4444' if count > 10 else '#f59e0b' if count > 5 else '#10b981'
        return format_html('<span style="color:{};font-weight:600;">{} open</span>', color, count)
    open_tickets.short_description = 'Open'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="background:#d1fae5;color:#065f46;padding:4px 12px;border-radius:6px;font-weight:600;">Active</span>')
        return format_html('<span style="background:#fee2e2;color:#991b1b;padding:4px 12px;border-radius:6px;font-weight:600;">Inactive</span>')
    is_active_badge.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(DepartmentMember)
class DepartmentMemberAdmin(admin.ModelAdmin):
    list_display   = ['user_info', 'department_badge', 'role_badge',
                      'permissions_summary', 'is_active_badge', 'joined_at']
    list_filter    = ['department', 'role', 'is_active', 'joined_at']
    search_fields  = ['user__username', 'user__email', 'department__name']
    readonly_fields = ['joined_at', 'added_by']

    fieldsets = (
        ('Member', {'fields': ('user', 'department', 'role', 'is_active')}),
        ('Permissions', {'fields': ('can_assign_tickets', 'can_close_tickets', 'can_delete_tickets')}),
        ('Metadata', {'fields': ('added_by', 'joined_at'), 'classes': ('collapse',)}),
    )

    def user_info(self, obj):
        return format_html('<strong>{}</strong><br><small style="color:#64748b;">{}</small>',
                           obj.user.get_full_name() or obj.user.username, obj.user.email)
    user_info.short_description = 'User'

    def department_badge(self, obj):
        return format_html(
            '<span style="background:{};color:white;padding:4px 12px;border-radius:6px;font-weight:600;">{}</span>',
            obj.department.color, obj.department.name
        )
    department_badge.short_description = 'Department'

    def role_badge(self, obj):
        colors = {'MEMBER':'#94a3b8'}
        return format_html(
            '<span style="background:{};color:white;padding:4px 12px;border-radius:6px;font-weight:600;">{}</span>',
            colors.get(obj.role, '#94a3b8'), obj.display_role
        )
    role_badge.short_description = 'Role'

    def permissions_summary(self, obj):
        perms = []
        if obj.can_assign_tickets: perms.append('Assign')
        if obj.can_close_tickets:  perms.append('Close')
        if obj.can_delete_tickets: perms.append('Delete')
        if perms:
            return format_html('<span style="color:#10b981;font-size:.875rem;">{}</span>', ', '.join(perms))
        return format_html('<span style="color:#94a3b8;">No special permissions</span>')
    permissions_summary.short_description = 'Permissions'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="background:#d1fae5;color:#065f46;padding:4px 12px;border-radius:6px;font-weight:600;">Active</span>')
        return format_html('<span style="background:#fee2e2;color:#991b1b;padding:4px 12px;border-radius:6px;font-weight:600;">Inactive</span>')
    is_active_badge.short_description = 'Status'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.added_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'department', 'Address', 'City', 'State', 'phone']
    list_filter   = ['department', 'City', 'State']
    search_fields = ['user__username', 'user__email', 'Address', 'phone']

@admin.register(TicketDetail)
class TicketDetailsAdmin(admin.ModelAdmin):
    list_display  = [
        'id', 'TICKET_TITLE', 'category', 'priority',
        'department_badge', 'TICKET_CREATED', 'TICKET_CLOSED',
        'TICKET_CREATED_ON', 'TICKET_DUE_DATE',
        'status_badge',
    ]
    list_filter   = [
        'TICKET_STATUS', 'priority', 'category', 'assigned_department',
        'TICKET_CREATED_ON', 'TICKET_DUE_DATE',
    ]
    search_fields = ['TICKET_TITLE', 'TICKET_DESCRIPTION', 'TICKET_HOLDER', 'TICKET_CREATED__username']
    date_hierarchy = 'TICKET_CREATED_ON'
    list_per_page  = 25
    readonly_fields = [
        'TICKET_CREATED_ON', 'TICKET_CLOSED_ON', 'updated_at', 'assigned_at', 'views_count',
    ]

    fieldsets = (
        ('Basic', {'fields': ('TICKET_TITLE', 'TICKET_DESCRIPTION', 'category')}),
        ('Assignment', {'fields': ('assigned_department', 'assigned_to', 'assignment_type', 'assigned_by', 'assigned_at')}),
        ('Legacy Assignment', {
            'fields': ('TICKET_CREATED', 'TICKET_HOLDER', 'TICKET_CLOSED', 'department'),
            'classes': ('collapse',),
        }),
        ('Status & Priority', {'fields': ('TICKET_STATUS', 'priority')}),
        ('Dates', {'fields': ('TICKET_DUE_DATE', 'TICKET_CREATED_ON', 'TICKET_CLOSED_ON', 'updated_at')}),
        ('AI/ML', {
            'classes': ('collapse',),
            'fields': ('ai_suggested_category', 'ai_suggested_priority',
                       'ml_predicted_department', 'ml_confidence_score',
                       'is_potential_duplicate', 'similar_to'),
        }),
    )

    def department_badge(self, obj):
        if obj.assigned_department:
            return format_html(
                '<span style="background:{};color:white;padding:4px 12px;border-radius:6px;font-weight:600;">'
                '<i class="{}"></i> {}</span>',
                obj.assigned_department.color, obj.assigned_department.icon, obj.assigned_department.name
            )
        return format_html('<span style="color:#94a3b8;">—</span>')
    department_badge.short_description = 'Department'

    def status_badge(self, obj):
        colors = {
            'Open':'#3b82f6','In Progress':'#f59e0b','Closed':'#94a3b8',
            'Resolved':'#10b981','Reopen':'#ef4444',
        }
        return format_html(
            '<span style="background:{};color:white;padding:4px 12px;border-radius:6px;font-weight:600;font-size:.75rem;">{}</span>',
            colors.get(obj.TICKET_STATUS, '#94a3b8'), obj.TICKET_STATUS
        )
    status_badge.short_description = 'Status'

@admin.register(MyCart)
class MyCartAdmin(admin.ModelAdmin):
    list_display  = ['id', 'user', 'ticket', 'ticket_count', 'accepted_at']
    list_filter   = ['accepted_at', 'user']
    search_fields = ['user__username', 'ticket__TICKET_TITLE']

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display   = ['id', 'user', 'action_badge', 'title', 'ticket_link', 'timestamp']
    list_filter    = ['action', 'timestamp']
    search_fields  = ['user__username', 'title', 'description', 'ticket__TICKET_TITLE']
    date_hierarchy = 'timestamp'
    ordering       = ['-timestamp']
    readonly_fields = ['user', 'ticket', 'action', 'title', 'description',
                       'old_value', 'new_value', 'timestamp']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def action_badge(self, obj):
        color = obj.get_color()
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;border-radius:6px;font-size:.75rem;font-weight:600;">{}</span>',
            color, obj.get_action_display()
        )
    action_badge.short_description = 'Action'

    def ticket_link(self, obj):
        if obj.ticket:
            return format_html(
                '<a href="/admin/myapp/ticketdetail/{}/change/">#{} {}</a>',
                obj.ticket.id, obj.ticket.id, obj.ticket.TICKET_TITLE[:40]
            )
        return '—'
    ticket_link.short_description = 'Ticket'

@admin.register(UserComment)
class UserCommentAdmin(admin.ModelAdmin):
    list_display  = ['id', 'user', 'ticket', 'created_at']
    list_filter   = ['created_at']
    search_fields = ['user__username', 'ticket__TICKET_TITLE', 'Reopen_comment', 'Closing_comment']
    readonly_fields = ['created_at']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'colored_badge', 'is_active', 'created_at']
    list_filter   = ['is_active', 'created_at']
    search_fields = ['name', 'description']

    fieldsets = (
        ('Basic', {'fields': ('name', 'description', 'is_active')}),
        ('Display', {'fields': ('icon', 'color')}),
        ('ML Keywords', {'fields': ('ml_keywords',)}),
    )

    def colored_badge(self, obj):
        return format_html(
            '<span style="background:{};color:white;padding:4px 12px;border-radius:6px;">'
            '<i class="{}"></i> {}</span>',
            obj.color, obj.icon, obj.name
        )
    colored_badge.short_description = 'Preview'


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display    = ['title', 'category', 'is_published', 'views', 'helpful_count', 'created_at']
    list_filter     = ['is_published', 'category', 'created_at']
    search_fields   = ['title', 'content', 'keywords']
    readonly_fields = ['views', 'helpful_count', 'created_at', 'updated_at']

    fieldsets = (
        ('Article', {'fields': ('title', 'content', 'category', 'is_published')}),
        ('Search & AI', {'fields': ('keywords',)}),
        ('Metadata', {'fields': ('created_by', 'views', 'helpful_count', 'created_at', 'updated_at'),
                      'classes': ('collapse',)}),
    )


@admin.register(AIMLLog)
class AIMLLogAdmin(admin.ModelAdmin):
    list_display    = ['ticket', 'log_type', 'confidence', 'was_correct', 'created_at']
    list_filter     = ['log_type', 'was_correct', 'created_at']
    search_fields   = ['ticket__TICKET_TITLE', 'input_data', 'output_data']
    readonly_fields = ['ticket', 'log_type', 'input_data', 'output_data', 'confidence', 'created_at']
    date_hierarchy  = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display    = ['id', 'user', 'notification_type', 'title', 'ticket',
                       'is_read', 'email_sent', 'created_at']
    list_filter     = ['notification_type', 'is_read', 'email_sent', 'created_at']
    search_fields   = ['user__username', 'user__email', 'title', 'message', 'ticket__TICKET_TITLE']
    readonly_fields = ['created_at', 'read_at', 'email_sent_at']
    list_per_page   = 50
    date_hierarchy  = 'created_at'

    fieldsets = (
        ('Basic', {'fields': ('user', 'ticket', 'notification_type')}),
        ('Content', {'fields': ('title', 'message', 'extra_data')}),
        ('Status', {'fields': ('is_read', 'read_at', 'email_sent', 'email_sent_at')}),
        ('Timestamps', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = 'Mark selected as read'

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{updated} notifications marked as unread.')
    mark_as_unread.short_description = 'Mark selected as unread'


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display    = ['ticket_link', 'action_type', 'changed_by', 'field_name', 'changed_at']
    list_filter     = ['action_type', 'changed_at']
    search_fields   = ['ticket__TICKET_TITLE', 'description', 'field_name']
    date_hierarchy  = 'changed_at'
    ordering        = ['-changed_at']
    readonly_fields = ['ticket', 'changed_by', 'action_type', 'field_name',
                       'old_value', 'new_value', 'description', 'changed_at']

    fieldsets = (
        ('Change', {'fields': ('ticket', 'changed_by', 'action_type', 'changed_at')}),
        ('Fields', {'fields': ('field_name', 'old_value', 'new_value')}),
        ('Description', {'fields': ('description',)}),
    )

    def ticket_link(self, obj):
        return format_html('<a href="/admin/myapp/ticketdetail/{}/change/">Ticket #{}</a>',
                           obj.ticket.id, obj.ticket.id)
    ticket_link.short_description = 'Ticket'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(CannedResponse)
class CannedResponseAdmin(admin.ModelAdmin):
    list_display    = ['title', 'category', 'department', 'usage_count',
                       'is_public', 'is_active', 'created_by', 'created_at']
    list_filter     = ['is_active', 'is_public', 'category', 'department']
    search_fields   = ['title', 'content']
    ordering        = ['-usage_count', 'title']
    readonly_fields = ['usage_count', 'created_by', 'created_at', 'updated_at']

    fieldsets = (
        ('Response', {'fields': ('title', 'content')}),
        ('Categorisation', {'fields': ('category', 'department', 'is_public', 'is_active')}),
        ('Usage', {'fields': ('usage_count', 'created_by', 'created_at', 'updated_at')}),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TicketRating)
class TicketRatingAdmin(admin.ModelAdmin):
    list_display    = ['ticket_link', 'rating_stars', 'rated_by', 'resolution_quality',
                       'response_time_rating', 'agent_helpfulness', 'rated_at']
    list_filter     = ['rating', 'resolution_quality', 'response_time_rating', 'agent_helpfulness']
    search_fields   = ['ticket__TICKET_TITLE', 'feedback', 'rated_by__username']
    date_hierarchy  = 'rated_at'
    ordering        = ['-rated_at']
    readonly_fields = ['ticket', 'rated_by', 'rated_at']

    fieldsets = (
        ('Rating', {'fields': ('ticket', 'rated_by', 'rating', 'rated_at')}),
        ('Detailed', {'fields': ('resolution_quality', 'response_time_rating', 'agent_helpfulness')}),
        ('Feedback', {'fields': ('feedback',)}),
    )

    def ticket_link(self, obj):
        return format_html('<a href="/admin/myapp/ticketdetail/{}/change/">Ticket #{}</a>',
                           obj.ticket.id, obj.ticket.id)
    ticket_link.short_description = 'Ticket'

    def rating_stars(self, obj):
        stars = '⭐' * obj.rating
        color = '#10b981' if obj.rating >= 4 else '#f59e0b' if obj.rating == 3 else '#ef4444'
        return format_html('<span style="color:{};font-size:16px;">{}</span>', color, stars)
    rating_stars.short_description = 'Rating'

admin.site.site_header = "Helpdesk Administration"
admin.site.site_title  = "Helpdesk Admin"
admin.site.index_title = "Welcome to Helpdesk Admin Panel"


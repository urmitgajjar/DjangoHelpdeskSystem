from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [

                                                                               
    path('',        views.landing_page, name='landing'),

                                                                               
                                        
    path('dashboard/',                  views.Basepage, name='base'),
    path('dashboard/admin/',            views.Basepage, name='admin_dashboard'),
                                                            
    path('dashboard/<int:dept_id>/',    views.Basepage, name='base_department'),
                              
    path('advanced/',                   views.advanced_dashboard, name='advanced_dashboard'),

                                                                               
    path('ticket/new/',            views.TicketDetails,        name='ticketdetail'),
    path('ticket/<int:pk>/',       views.TicketInfo,            name='ticketinfo'),
    path('ticket/<int:pk>/edit/',  views.updateticket,         name='updateticket'),
    path('ticket/<int:pk>/reassign/', views.admin_reassign_ticket, name='admin_reassign_ticket'),
    path('ticket/<int:pk>/delete/',views.deleteticket,         name='deleteticket'),
    path('tickets/bulk-delete/',   views.bulk_delete_tickets, name='bulk_delete_tickets'),
    path('ticket/<int:pk>/reject/',views.RemoveTicket,         name='removeticket'),
    path('ticket/<int:pk>/close/', views.CloseTicket,          name='closeticket'),
    path('ticket/<int:pk>/reopen/',views.reopenticket,         name='reopenticket'),
    path('ticket/<int:pk>/resolve/',views.resolvedticket,     name='resolvedticket'),
    path('ticket/<int:pk>/history/',views.ticket_history,     name='ticket_history'),
    path('ticket/<int:pk>/rate/',  views.rate_ticket,          name='rate_ticket'),
    path('ticket/<int:pk>/overdue-note/', views.send_overdue_note, name='send_overdue_note'),
    path('ticket/<int:pk>/overdue-note-reply/', views.reply_overdue_note, name='reply_overdue_note'),

                                                
    path('my-tickets/',            views.MyCarts,            name='mycart'),

                                                                               
    path('login/',    views.LoginView,    name='login'),
    path('logout/',   views.LogoutView,   name='logout'),
    path('register/', views.RegisterView, name='register'),

    path('change-password/', views.Change_Password, name='ChangePassword'),

    path(
        'password-reset/',
        views.UsernameRequiredPasswordResetView.as_view(
            template_name='password_reset_form.html',
            email_template_name='password_reset_email.txt',
            subject_template_name='password_reset_subject.txt',
            html_email_template_name='password_reset_email.html',
        ),
        name='password_reset'
    ),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'),
         name='password_reset_complete'),

                                                                               
    path('profile/',                 views.User_Profile,   name='profile'),
    path('profile/edit/<int:pk>/',   views.update_profile, name='update_profile'),

                                                                               
    path('resolved-history/',        views.resolved_history,    name='resolved_history'),
    path('activity/',                views.activity_log,        name='activity_log'),

                                                                               
    path('account-settings/',        views.account_settings,    name='account_settings'),

                                                                               
    path('ticket/<int:pk>/comment/<str:action>/', views.comment_view,  name='comment'),
    path('download/<int:pk>/',                    views.download_file, name='download_file'),

                                                                               
    path('categories/',                 views.category_list,   name='category_list'),
    path('categories/new/',             views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/',   views.category_edit,   name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

                                                                               
    path('pie-chart/',     views.pie_chart,    name='pie_chart'),
    path('bar-chart/',     views.Bar_chart,    name='bar_chart'),

                                                                                
                                                              
    path('department/<int:dept_id>/',
         views.department_dashboard,
         name='department_dashboard_id'),
                                                       
    path('department/',
         views.department_dashboard,
         name='department_dashboard'),
                                                                  
    path('department/members/',
         views.department_members,
         name='department_members'),
    path('department/<int:dept_id>/members/',
         views.department_members,
         name='department_members_id'),
                          
    path('department/<int:dept_id>/analytics/',
         views.department_analytics,
         name='department_analytics'),

                                                                               
    path('admin-departments/',
         views.admin_department_list,
         name='admin_department_list'),
    path('admin-departments/<int:dept_id>/tickets/',
         views.admin_department_tickets,
         name='admin_department_tickets'),
    path('admin-departments/create/',
         views.admin_create_department,
         name='admin_create_department'),
    path('admin-departments/<int:dept_id>/update/',
         views.admin_update_department,
         name='admin_update_department'),
    path('admin-departments/<int:dept_id>/delete/',
         views.admin_delete_department,
         name='admin_delete_department'),
    path('admin-departments/<int:dept_id>/reactivate/',
         views.admin_reactivate_department,
         name='admin_reactivate_department'),
    path('admin-departments/inactive/delete/',
         views.admin_permanently_delete_inactive_department,
         name='admin_permanently_delete_inactive_department'),
    path('admin-departments/<int:dept_id>/add-member/',
         views.admin_add_member,
         name='admin_add_member'),
    path('admin-departments/<int:dept_id>/remove-member/<int:user_id>/',
         views.admin_remove_member,
         name='admin_remove_member'),

                                                                               
    path('notifications/',
         views.notifications_list,
         name='notifications_list'),
    path('notifications/<int:notification_id>/read/',
         views.mark_notification_read,
         name='mark_notification_read'),
    path('notifications/mark-all-read/',
         views.mark_all_read,
         name='mark_all_read'),
    path('notifications/delete-all/',
         views.delete_all_notifications,
         name='delete_all_notifications'),
    path('notifications/<int:notification_id>/delete/',
         views.delete_notification,
         name='delete_notification'),

                                                                               
    path('api/notification-count/',     views.notification_count_api,     name='notification_count_api'),
    path('api/username-exists/',        views.username_exists_api,        name='username_exists_api'),
    path('api/tickets-over-time/',        views.api_tickets_over_time,        name='api_tickets_over_time'),
    path('api/department-comparison/',  views.api_department_comparison,  name='api_department_comparison'),
    path('api/priority-distribution/',  views.api_priority_distribution,  name='api_priority_distribution'),
    path('api/category-distribution/',  views.api_category_distribution,  name='api_category_distribution'),

                                                                               
    path('analytics/',                  views.analytics_dashboard,    name='analytics_dashboard'),
    path('analytics/export/excel/',     views.export_analytics_excel, name='export_analytics_excel'),
    path('analytics/export/pdf/',       views.export_analytics_pdf,   name='export_analytics_pdf'),
]

from django.urls import resolve
from .models import get_visible_active_memberships


class DepartmentAccessMiddleware:                                                          
    EXEMPT_URL_NAMES = {
        'landing',
        'login',
        'logout',
        'register',
        'password_reset',
        'password_reset_done',
        'password_reset_confirm',
        'password_reset_complete',
        'profile',
        'update_profile',
        'ChangePassword',
        'notification_count_api',
        'notifications_list',
        'mark_notification_read',
        'mark_all_read',
        'delete_notification',
    }

                                                    
    EXEMPT_PATH_PREFIXES = (
        '/admin/',
        '/static/',
        '/media/',
        '/api/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

                                                 
        if request.user.is_superuser or getattr(request.user, 'is_staff', False):
            return self.get_response(request)

        path = request.path

                                                         
        if any(path.startswith(p) for p in self.EXEMPT_PATH_PREFIXES):
            return self.get_response(request)

                                                      
        try:
            current_url_name = resolve(path).url_name
        except Exception:
            current_url_name = ''

        if current_url_name in self.EXEMPT_URL_NAMES:
            return self.get_response(request)

                                                                        
        request.user_departments = get_visible_active_memberships(request.user)

        return self.get_response(request)


class TicketAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

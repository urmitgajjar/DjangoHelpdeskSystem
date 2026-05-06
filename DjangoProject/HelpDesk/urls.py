from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.contrib.staticfiles.views import serve
from django.urls import re_path


def favicon_view(_request):
    return HttpResponse(status=204)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("myapp.urls")),
    path("favicon.ico", favicon_view, name="favicon"),
]

# Serve static and media files regardless of DEBUG setting
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve static files when DEBUG=False (admin CSS fix)
urlpatterns += [
    re_path(r'^static/(?P<path>.*)$', serve, {'insecure': True}),
]

admin.site.site_header = "Helpdesk Administration"
admin.site.site_title = "Helpdesk Admin Portal"
admin.site.index_title = "Welcome to Helpdesk Admin Panel"
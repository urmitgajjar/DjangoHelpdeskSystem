from django.apps import AppConfig

class MyappConfig(AppConfig):
    name               = "myapp"
    default_auto_field = 'django.db.models.BigAutoField'
    verbose_name       = "Helpdesk Management System"

    def ready(self):
        pass

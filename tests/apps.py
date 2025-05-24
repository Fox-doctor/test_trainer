from django.apps import AppConfig
from django.contrib.auth import get_user_model
import os

class TestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tests'

    def ready(self):
        import tests.signals

        # Создание суперпользователя при запуске приложения
        User = get_user_model()
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "fox")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "Transformator11")

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)

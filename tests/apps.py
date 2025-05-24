# tests/apps.py
from django.apps import AppConfig

class TestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tests'

    def ready(self):
        # Регистрация сигналов (если они нужны)
        import tests.signals

        # Программное создание суперпользователя, если его нет.
        # **Обратите внимание:** этот код выполнится каждый раз при старте приложения,
        # поэтому рекомендуется использовать его только временно, а после успешного деплоя удалить.
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            try:
                # Задайте нужные вам логин, email и пароль
                User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='adminpassword'
                )
                print("Superuser успешно создан.")
            except Exception as e:
                print("Ошибка при создании суперпользователя:", e)

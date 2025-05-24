# tests/apps.py
from django.apps import AppConfig

class TestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tests'

    def ready(self):
        # Импорт сигналов, если они вам нужны
        import tests.signals

        # Добавим временный код для создания суперпользователя.
        # Оборачиваем весь блок в try/except, чтобы избежать ошибки, если таблицы ещё не созданы.
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if not User.objects.filter(is_superuser=True).exists():
                # Создаём суперпользователя
                User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='adminpassword'
                )
                print("Superuser успешно создан.")
        except Exception as e:
            # Если возникает ошибка (например, таблицы еще не созданы), пропускаем создание суперпользователя.
            print("Не удалось создать суперпользователя:", e)

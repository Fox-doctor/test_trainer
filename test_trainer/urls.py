from django.contrib import admin
from django.urls import path, include
from tests.views import user_admin_view

urlpatterns = [
    path('user_admin/', user_admin_view, name='user_admin'),
    path('admin/', admin.site.urls),
    path('', include('tests.urls')),  # Корневой URL сервера обрабатывается приложением tests
    path('accounts/', include('django.contrib.auth.urls')),  # добавляет маршруты для login, logout, password_change и т.д.
]

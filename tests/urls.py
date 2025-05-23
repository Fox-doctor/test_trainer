from django.urls import path
from .views import edit_user_view, user_statistics, user_admin_view
from .views import import_questions_text
from .views import (
    home, select_test, training_test, test_page, test_view, my_results, training_statistics,
    question_list, question_create, question_edit, question_delete, training_results
)

urlpatterns = [
    path('', home, name='home'),                           # Корневой путь приложения tests
    path('select_test/', select_test, name='select_test'),   # Страница выбора теста
    path('training_test/', training_test, name='training_test'),
    path('training_results/', training_results, name='training_results'),
    path('test/', test_page, name='test_page'),              # Страница прохождения теста с выбранными параметрами
    path('test_view/', test_view, name='test_view'),
    path('results/', test_view, name='results'),  # Обработка результатов теста
    path('my_results/', my_results, name='my_results'), # Новый маршрут для истории результатов
    path('training_statistics/', training_statistics, name='training_statistics'),
    path('moderator/questions/import/', import_questions_text, name='import_questions_text'), # Загрузка вопросов из файла

    # path('admin/users/', user_admin_view, name='user_admin'),  <-- эта строка удалена (или переименована)
    path('progress/', user_statistics, name='user_statistics'),

    path('user_admin/<int:user_id>/edit/', edit_user_view, name='edit_user'), # маршруты модератора и т.д.

    # Маршруты для управления вопросами модератором:
    path('moderator/questions/', question_list, name='question_list'),
    path('moderator/questions/add/', question_create, name='question_create'),
    path('moderator/questions/<int:pk>/edit/', question_edit, name='question_edit'),
    path('moderator/questions/<int:pk>/delete/', question_delete, name='question_delete'),
]

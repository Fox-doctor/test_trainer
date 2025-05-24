from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

#Создание модели для ведения статистики по тренажерным тестам
User = get_user_model()
class TrainingTestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=100, blank=True)
    section = models.CharField(max_length=100, blank=True)
    score = models.IntegerField()
    total_questions = models.IntegerField()
    details = models.TextField(help_text="JSON-строка с подробностями о запросе", blank=True)
    taken_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TrainingTestResult(id={self.id}, user={self.user}, score={self.score}/{self.total_questions})"


# Константы для вариантов выбора
SUBJECT_CHOICES = [
    ('science', 'Естествознание'),
    ('math', 'Математика'),
    ('logic', 'Логика и количественные характеристики'),
    ('Kazakh', 'Казахский язык'),
    ('Russian', 'Русский язык'),
    ('English', 'Английский язык'),
]

SECTION_CHOICES = [
    ('world_science', 'Мир науки'),
    ('human_earth', 'Человек, Земля, Вселенная'),
    ('materials', 'Вещества и материалы'),
    ('nature', 'Живая/Неживая природа'),
    ('energy_motion', 'Энергия и движение'),
    ('ecology', 'Экология и экосистемы'),
    ('politics', 'Политическая карта'),
]

class TestResult(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Пользователь"
    )
    # Используем choices для поля subject и section
    subject = models.CharField(
        max_length=100,
        choices=SUBJECT_CHOICES,
        verbose_name="Предмет"
    )
    section = models.CharField(
        max_length=100,
        choices=SECTION_CHOICES,
        verbose_name="Раздел"
    )
    score = models.PositiveIntegerField(verbose_name="Набранное количество баллов")
    total_questions = models.PositiveIntegerField(verbose_name="Общее число вопросов")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата прохождения")
    details = models.TextField(
        blank=True,
        verbose_name="Детали теста (опционально)"
    )

    def __str__(self):
        user_str = self.user.username if self.user else "Аноним"
        # Используем get_field_display для получения читаемых вариантов
        return f"{user_str}: {self.get_subject_display()} / {self.get_section_display()} - {self.score}/{self.total_questions}"


class Question(models.Model):
    subject = models.CharField(
        max_length=30,
        choices=SUBJECT_CHOICES,
        verbose_name="Предмет"
    )
    section = models.CharField(
        max_length=30,
        choices=SECTION_CHOICES,
        verbose_name="Раздел"
    )
    question_text = models.TextField(verbose_name="Вопрос")
    option1 = models.CharField(max_length=255, verbose_name="Вариант 1")
    option2 = models.CharField(max_length=255, verbose_name="Вариант 2")
    option3 = models.CharField(max_length=255, verbose_name="Вариант 3")
    option4 = models.CharField(max_length=255, verbose_name="Вариант 4")
    correct_option = models.IntegerField(
        choices=[(1, 'Вариант 1'), (2, 'Вариант 2'), (3, 'Вариант 3'), (4, 'Вариант 4')],
        verbose_name="Правильный вариант"
    )

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    access_exp_date = models.DateTimeField(blank=True, null=True, verbose_name="Дата истечения срока доступа")

    def __str__(self):
        return f"Профиль пользователя {self.user.username}"


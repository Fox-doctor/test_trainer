# tests/forms.py
from django import forms
from .models import Question
from django.contrib.auth.models import User


class UserEditForm(forms.ModelForm):
    # Добавляем поле для срока доступа – принимаем его как строку с типом datetime
    access_exp_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Дата истечения срока доступа"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        # Передаем профиль пользователя через дополнительный параметр
        self.profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)
        if self.profile and self.profile.access_exp_date:
            # Преобразуем значение к корректному формату для datetime-local
            self.fields['access_exp_date'].initial = self.profile.access_exp_date.strftime("%Y-%m-%dT%H:%M")

    def save(self, commit=True):
        user = super().save(commit)
        # Сохраняем поле доступа в связанном профиле
        if self.profile:
            self.profile.access_exp_date = self.cleaned_data.get('access_exp_date')
            if commit:
                self.profile.save()
        return user


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = [
            'subject',
            'section',
            'question_text',
            'option1',
            'option2',
            'option3',
            'option4',
            'correct_option'
        ]


class TestSelectionForm(forms.Form):
    SUBJECT_CHOICES = [
        ('science', 'Естествознание'),
        # Добавьте другие предметы при необходимости
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

    subject = forms.ChoiceField(choices=SUBJECT_CHOICES, label="Предмет")
    section = forms.ChoiceField(choices=SECTION_CHOICES, label="Раздел")


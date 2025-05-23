
from django.contrib import admin
from .models import Question, TestResult

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question_text', 'get_subject_display', 'get_section_display', 'correct_option')
    list_filter = ('subject', 'section')
    search_fields = ('question_text',)
    ordering = ('id',)

@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'get_subject_display', 'get_section_display', 'score', 'total_questions', 'date')
    list_filter = ('subject', 'section', 'date')
    search_fields = ('user__username',)
    ordering = ('-date',)

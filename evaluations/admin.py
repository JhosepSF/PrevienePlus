from django.contrib import admin
from evaluations.models import Dimension, Assessment, Question, AnswerOption, StudentAssessment, StudentResponse

class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 3

@admin.register(Dimension)
class DimensionAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'order')
    ordering = ('order',)

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'assessment_type', 'is_active', 'created_at')
    list_filter = ('assessment_type', 'is_active')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'order', 'dimension', 'question_text_truncated', 'question_type', 'weight', 'is_active')
    list_filter = ('assessment', 'dimension', 'question_type', 'is_active')
    inlines = [AnswerOptionInline]
    ordering = ('assessment', 'order')

    def question_text_truncated(self, obj):
        return obj.question_text[:75] + '...' if len(obj.question_text) > 75 else obj.question_text
    question_text_truncated.short_description = 'Enunciado'

class StudentResponseInline(admin.TabularInline):
    model = StudentResponse
    extra = 0
    readonly_fields = ('question', 'selected_option', 'score_obtained', 'answered_at')
    can_delete = False

@admin.register(StudentAssessment)
class StudentAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'assessment_type', 'score_dimension_1', 'score_dimension_2', 'total_score', 'is_submitted', 'started_at', 'completed_at')
    list_filter = ('assessment_type', 'is_submitted')
    search_fields = ('student__student_code',)
    readonly_fields = ('started_at', 'completed_at', 'score_dimension_1', 'score_dimension_2', 'total_score', 'is_submitted')
    inlines = [StudentResponseInline]

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from accounts.models import User, StudentProfile

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'role', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información de Investigación', {'fields': ('role',)}),
    )

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('student_code', 'group', 'stage', 'consent_given', 'intervention_completed', 'is_active', 'created_at')
    list_filter = ('group', 'stage', 'consent_given', 'intervention_completed', 'is_active')
    search_fields = ('student_code',)
    readonly_fields = ('created_at', 'updated_at', 'consent_timestamp', 'intervention_completed_at')

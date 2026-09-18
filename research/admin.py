from django.contrib import admin
from research.models import ResearchSetting, ExportAuditLog

@admin.register(ResearchSetting)
class ResearchSettingAdmin(admin.ModelAdmin):
    list_display = ('study_title', 'pretest_stage_open', 'intervention_stage_open', 'postest_stage_open', 'updated_at')

@admin.register(ExportAuditLog)
class ExportAuditLogAdmin(admin.ModelAdmin):
    list_display = ('dataset_type', 'file_format', 'records_count', 'researcher', 'exported_at')
    list_filter = ('dataset_type', 'file_format', 'exported_at')
    readonly_fields = ('dataset_type', 'file_format', 'records_count', 'researcher', 'exported_at')

from django.contrib import admin
from chatbot.models import ChatSession, ChatMessage, InterventionConfigLog

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('role', 'content', 'sources_used', 'topics_detected', 'tokens_used', 'created_at')
    can_delete = False

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('student', 'session_uuid_truncated', 'total_messages', 'duration_seconds', 'is_active', 'started_at', 'ended_at')
    list_filter = ('is_active', 'started_at')
    search_fields = ('student__student_code', 'session_uuid')
    inlines = [ChatMessageInline]

    def session_uuid_truncated(self, obj):
        return str(obj.session_uuid)[:8] + '...'
    session_uuid_truncated.short_description = 'UUID'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'content_truncated', 'topics_detected', 'tokens_used', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content', 'topics_detected', 'sources_used')

    def content_truncated(self, obj):
        return obj.content[:75] + '...' if len(obj.content) > 75 else obj.content
    content_truncated.short_description = 'Mensaje'

@admin.register(InterventionConfigLog)
class InterventionConfigLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'model_name', 'app_version', 'system_prompt_version', 'temperature', 'knowledge_chunks_count', 'recorded_at')
    list_filter = ('model_name', 'system_prompt_version', 'app_version')
    search_fields = ('student__student_code', 'model_name')
    readonly_fields = ('student', 'session', 'app_version', 'model_name', 'temperature', 'system_prompt_version', 'system_prompt_text', 'knowledge_chunks_count', 'recorded_at')

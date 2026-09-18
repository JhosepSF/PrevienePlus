from django.contrib import admin
from knowledge.models import KnowledgeCategory, KnowledgeDocument, KnowledgeChunk

@admin.register(KnowledgeCategory)
class KnowledgeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'order')
    prepopulated_fields = {'code': ('name',)}
    ordering = ('order', 'name')

class KnowledgeChunkInline(admin.StackedInline):
    model = KnowledgeChunk
    extra = 0
    fields = ('order', 'chunk_text', 'keywords', 'is_active')
    readonly_fields = ('keywords',)

@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'source_institution', 'publication_year', 'is_active', 'updated_at')
    list_filter = ('category', 'source_institution', 'publication_year', 'is_active')
    search_fields = ('title', 'full_content', 'source_institution')
    inlines = [KnowledgeChunkInline]

@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'category', 'chunk_text_truncated', 'is_active')
    list_filter = ('category', 'is_active', 'document__source_institution')
    search_fields = ('chunk_text', 'keywords')

    def chunk_text_truncated(self, obj):
        return obj.chunk_text[:90] + '...' if len(obj.chunk_text) > 90 else obj.chunk_text
    chunk_text_truncated.short_description = 'Fragmento'

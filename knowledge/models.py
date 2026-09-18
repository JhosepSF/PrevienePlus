from django.db import models
from django.utils.translation import gettext_lazy as _

class KnowledgeCategory(models.Model):
    """
    Categories of STI educational topics (HIV, HPV, Syphilis, Condom usage, Myths, etc.)
    """
    name = models.CharField(max_length=150, unique=True, verbose_name=_('Nombre de la Categoría'))
    code = models.SlugField(max_length=100, unique=True, verbose_name=_('Código / Slug'))
    description = models.TextField(blank=True, verbose_name=_('Descripción'))
    icon = models.CharField(max_length=50, default='bi-shield-check', verbose_name=_('Icono Bootstrap'))
    order = models.PositiveIntegerField(default=1, verbose_name=_('Orden'))

    class Meta:
        verbose_name = _('Categoría de Conocimiento')
        verbose_name_plural = _('Categorías de Conocimiento')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

class KnowledgeDocument(models.Model):
    """
    Validated scientific and institutional source document (MINSA, OMS, OPS).
    """
    title = models.CharField(max_length=255, verbose_name=_('Título del Documento'))
    category = models.ForeignKey(
        KnowledgeCategory,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('Categoría Principal')
    )
    source_institution = models.CharField(
        max_length=200,
        verbose_name=_('Institución / Fuente (ej. MINSA, OMS, OPS)')
    )
    publication_year = models.PositiveIntegerField(
        default=2024,
        verbose_name=_('Año de Publicación')
    )
    reference_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Referencia Bibliográfica o URL Oficial')
    )
    full_content = models.TextField(
        verbose_name=_('Contenido Completo del Documento')
    )
    summary = models.TextField(
        blank=True,
        verbose_name=_('Resumen Educativo')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo para Recuperación RAG')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Documento de Conocimiento')
        verbose_name_plural = _('Documentos de Conocimiento')
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.source_institution}, {self.publication_year})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from knowledge.services import sync_document_chunks
        sync_document_chunks(self)

class KnowledgeChunk(models.Model):
    """
    Normalized text chunk used in the RAG retrieval pipeline.
    """
    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name='chunks',
        verbose_name=_('Documento Origen')
    )
    category = models.ForeignKey(
        KnowledgeCategory,
        on_delete=models.CASCADE,
        related_name='chunks',
        verbose_name=_('Categoría')
    )
    chunk_text = models.TextField(
        verbose_name=_('Texto del Fragmento')
    )
    keywords = models.TextField(
        blank=True,
        verbose_name=_('Palabras Clave / Términos de Búsqueda')
    )
    order = models.PositiveIntegerField(
        default=1,
        verbose_name=_('Orden dentro del Documento')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo')
    )

    class Meta:
        verbose_name = _('Fragmento de Conocimiento (RAG Chunk)')
        verbose_name_plural = _('Fragmentos de Conocimiento (RAG Chunks)')
        ordering = ['document', 'order']

    def __str__(self):
        return f"[{self.category.name}] {self.chunk_text[:80]}..."

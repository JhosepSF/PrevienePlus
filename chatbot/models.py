import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from accounts.models import StudentProfile

class MessageRole(models.TextChoices):
    USER = 'user', _('Estudiante')
    ASSISTANT = 'assistant', _('Previene+ (IA)')
    SYSTEM = 'system', _('Sistema')

class ChatSession(models.Model):
    """
    Session of interaction with the Previene+ chatbot.
    """
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        verbose_name=_('Estudiante')
    )
    session_uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_('UUID de Sesión')
    )
    started_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Hora de Inicio')
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Hora de Cierre')
    )
    total_messages = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total de Mensajes')
    )
    duration_seconds = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Duración Total (Segundos)')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Sesión Activa')
    )

    class Meta:
        verbose_name = _('Sesión de Chatbot')
        verbose_name_plural = _('Sesiones de Chatbot')
        ordering = ['-started_at']

    def __str__(self):
        return f"Sesión {self.session_uuid.hex[:8]} - {self.student.student_code} ({self.total_messages} msgs)"

    def update_activity(self):
        self.total_messages = self.messages.count()
        if self.started_at:
            delta = timezone.now() - self.started_at
            self.duration_seconds = max(0, int(delta.total_seconds()))
        self.save(update_fields=['total_messages', 'duration_seconds'])

class ChatMessage(models.Model):
    """
    Individual message within a Previene+ educational chat session.
    """
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Sesión')
    )
    role = models.CharField(
        max_length=20,
        choices=MessageRole.choices,
        default=MessageRole.USER,
        verbose_name=_('Emisor')
    )
    content = models.TextField(
        verbose_name=_('Contenido del Mensaje')
    )
    sources_used = models.TextField(
        blank=True,
        verbose_name=_('Fuentes Validadas Utilizadas (RAG)')
    )
    topics_detected = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Temáticas Detectadas')
    )
    tokens_used = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Tokens Consumidos')
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Fecha y Hora')
    )

    class Meta:
        verbose_name = _('Mensaje de Chat')
        verbose_name_plural = _('Mensajes de Chat')
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.get_role_display()}] {self.content[:60]}..."

class InterventionConfigLog(models.Model):
    """
    Immutable log for scientific reproducibility.
    Records the exact AI configuration, prompt version, and knowledge base state
    active during the student's intervention.
    """
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='intervention_logs',
        verbose_name=_('Estudiante')
    )
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='config_logs',
        verbose_name=_('Sesión')
    )
    app_version = models.CharField(
        max_length=50,
        verbose_name=_('Versión de Previene+')
    )
    model_name = models.CharField(
        max_length=100,
        verbose_name=_('Modelo de Lenguaje (OpenAI)')
    )
    temperature = models.FloatField(
        default=0.3,
        verbose_name=_('Temperatura de Muestreo')
    )
    system_prompt_version = models.CharField(
        max_length=50,
        default='v1.0-research-safe',
        verbose_name=_('Versión del System Prompt')
    )
    system_prompt_text = models.TextField(
        verbose_name=_('Texto del System Prompt')
    )
    knowledge_chunks_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total de Fragmentos RAG Disponibles')
    )
    recorded_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Fecha de Registro')
    )

    class Meta:
        verbose_name = _('Registro de Reproducibilidad Científica')
        verbose_name_plural = _('Registros de Reproducibilidad Científica')
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.student.student_code} - {self.model_name} ({self.recorded_at.strftime('%d/%m/%Y %H:%M')})"

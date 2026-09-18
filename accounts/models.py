from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', _('Administrador')
    RESEARCHER = 'RESEARCHER', _('Investigador')
    STUDENT = 'STUDENT', _('Estudiante')

class ResearchGroup(models.TextChoices):
    EXPERIMENTAL = 'EXPERIMENTAL', _('Grupo Experimental (Previene+)')
    CONTROL = 'CONTROL', _('Grupo Control (Tradicional)')

class StudyStage(models.TextChoices):
    CONSENT = 'CONSENT', _('Asentimiento / Consentimiento')
    PRETEST = 'PRETEST', _('Pretest')
    INTERVENTION = 'INTERVENTION', _('Intervención')
    POSTEST = 'POSTEST', _('Postest')
    COMPLETED = 'COMPLETED', _('Completado')

class User(AbstractUser):
    """
    Custom user model supporting Administrators, Researchers and Pseudonymized Students.
    """
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.STUDENT,
        verbose_name=_('Rol de usuario')
    )

    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    @property
    def is_researcher_or_admin(self):
        return self.role in [UserRole.ADMIN, UserRole.RESEARCHER] or self.is_superuser or self.is_staff

class StudentProfile(models.Model):
    """
    Pseudonymized profile for school participants in the quasi-experimental study.
    Strictly avoids storing personal identifiable information (PII).
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name=_('Usuario del sistema')
    )
    student_code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        verbose_name=_('Código Pseudonimizado (ej. EXP-001, CTR-001)')
    )
    group = models.CharField(
        max_length=20,
        choices=ResearchGroup.choices,
        default=ResearchGroup.EXPERIMENTAL,
        verbose_name=_('Grupo de Investigación')
    )
    stage = models.CharField(
        max_length=20,
        choices=StudyStage.choices,
        default=StudyStage.CONSENT,
        verbose_name=_('Etapa Actual')
    )
    consent_given = models.BooleanField(
        default=False,
        verbose_name=_('Asentimiento/Consentimiento Aceptado')
    )
    consent_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Fecha y Hora de Asentimiento')
    )
    intervention_completed = models.BooleanField(
        default=False,
        verbose_name=_('Intervención Completada')
    )
    intervention_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de Fin de Intervención')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Participante Activo')
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Notas del Investigador (Opcional)')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Registro')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Actualización')
    )

    class Meta:
        verbose_name = _('Perfil de Estudiante')
        verbose_name_plural = _('Perfiles de Estudiantes')
        ordering = ['student_code']

    def __str__(self):
        return f"{self.student_code} ({self.get_group_display()})"

    @property
    def is_experimental(self):
        return self.group == ResearchGroup.EXPERIMENTAL

    @property
    def is_control(self):
        return self.group == ResearchGroup.CONTROL

    def can_access_pretest(self):
        """Pretest is available once consent is accepted and stage is at least PRETEST."""
        return self.consent_given and self.stage in [StudyStage.PRETEST, StudyStage.INTERVENTION, StudyStage.POSTEST, StudyStage.COMPLETED]

    def can_access_intervention(self):
        """Intervention is only available for experimental group after completing pretest."""
        return self.is_experimental and self.stage in [StudyStage.INTERVENTION, StudyStage.POSTEST, StudyStage.COMPLETED]

    def can_access_postest(self):
        """Postest is accessible when pretest is done and intervention condition is fulfilled."""
        return self.stage in [StudyStage.POSTEST, StudyStage.COMPLETED]

    def advance_stage_after_pretest(self):
        if self.is_experimental:
            self.stage = StudyStage.INTERVENTION
        else:
            # Control group moves to postest stage or waits for traditional intervention
            self.stage = StudyStage.POSTEST
        self.save(update_fields=['stage', 'updated_at'])

    def complete_intervention(self):
        self.intervention_completed = True
        self.intervention_completed_at = timezone.now()
        self.stage = StudyStage.POSTEST
        self.save(update_fields=['intervention_completed', 'intervention_completed_at', 'stage', 'updated_at'])

    def complete_postest(self):
        self.stage = StudyStage.COMPLETED
        self.save(update_fields=['stage', 'updated_at'])

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from accounts.models import StudentProfile

class AssessmentType(models.TextChoices):
    PRETEST = 'PRETEST', _('Pretest')
    POSTEST = 'POSTEST', _('Postest')

class QuestionType(models.TextChoices):
    MULTIPLE_CHOICE = 'MULTIPLE_CHOICE', _('Opción Múltiple')
    TRUE_FALSE = 'TRUE_FALSE', _('Verdadero / Falso')
    LIKERT = 'LIKERT', _('Escala Likert (Frecuencia / Acuerdo)')

class Dimension(models.Model):
    """
    Evaluation dimension for quasi-experimental measurement:
    Dimensión 1: Conocimientos sobre prevención de ITS
    Dimensión 2: Prácticas preventivas frente a ITS
    """
    code = models.CharField(max_length=50, unique=True, verbose_name=_('Código de Dimensión'))
    name = models.CharField(max_length=200, verbose_name=_('Nombre de la Dimensión'))
    description = models.TextField(blank=True, verbose_name=_('Descripción'))
    order = models.PositiveIntegerField(default=1, verbose_name=_('Orden'))

    class Meta:
        verbose_name = _('Dimensión de Evaluación')
        verbose_name_plural = _('Dimensiones de Evaluación')
        ordering = ['order', 'id']

    def __str__(self):
        return self.name

class Assessment(models.Model):
    """
    Assessment instrument configuration (Pretest / Postest).
    """
    assessment_type = models.CharField(
        max_length=20,
        choices=AssessmentType.choices,
        unique=True,
        verbose_name=_('Tipo de Evaluación')
    )
    title = models.CharField(max_length=255, verbose_name=_('Título'))
    instructions = models.TextField(verbose_name=_('Instrucciones para el Estudiante'))
    is_active = models.BooleanField(default=True, verbose_name=_('Activo'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Instrumento de Evaluación')
        verbose_name_plural = _('Instrumentos de Evaluación')

    def __str__(self):
        return f"{self.get_assessment_type_display()} - {self.title}"

class Question(models.Model):
    """
    Question item linked to an assessment instrument and dimension.
    """
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_('Instrumento')
    )
    dimension = models.ForeignKey(
        Dimension,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_('Dimensión')
    )
    question_text = models.TextField(verbose_name=_('Enunciado de la Pregunta'))
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.MULTIPLE_CHOICE,
        verbose_name=_('Tipo de Pregunta')
    )
    weight = models.FloatField(default=1.0, verbose_name=_('Puntaje Máximo / Peso'))
    order = models.PositiveIntegerField(default=1, verbose_name=_('Orden'))
    is_active = models.BooleanField(default=True, verbose_name=_('Activa'))

    class Meta:
        verbose_name = _('Pregunta')
        verbose_name_plural = _('Preguntas')
        ordering = ['assessment', 'order', 'id']

    def __str__(self):
        return f"[{self.assessment.get_assessment_type_display()}] P{self.order}: {self.question_text[:60]}..."

class AnswerOption(models.Model):
    """
    Answer choice for a given question.
    """
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name=_('Pregunta')
    )
    option_text = models.CharField(max_length=350, verbose_name=_('Texto de la Opción'))
    score_value = models.FloatField(default=0.0, verbose_name=_('Valor / Puntaje'))
    is_correct = models.BooleanField(default=False, verbose_name=_('¿Es la opción correcta? (para conocimientos)'))
    order = models.PositiveIntegerField(default=1, verbose_name=_('Orden'))

    class Meta:
        verbose_name = _('Opción de Respuesta')
        verbose_name_plural = _('Opciones de Respuesta')
        ordering = ['question', 'order', 'id']

    def __str__(self):
        return f"{self.option_text} ({self.score_value} pts)"

class StudentAssessment(models.Model):
    """
    Completed or in-progress assessment attempt by a pseudonymized student.
    Guarantees that once submitted, it cannot be modified by the student.
    """
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='student_assessments',
        verbose_name=_('Estudiante')
    )
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.PROTECT,
        related_name='student_submissions',
        verbose_name=_('Instrumento')
    )
    assessment_type = models.CharField(
        max_length=20,
        choices=AssessmentType.choices,
        verbose_name=_('Tipo de Evaluación')
    )
    started_at = models.DateTimeField(default=timezone.now, verbose_name=_('Fecha y Hora de Inicio'))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Fecha y Hora de Finalización'))
    score_dimension_1 = models.FloatField(default=0.0, verbose_name=_('Puntaje Dimensión 1 (Conocimientos)'))
    score_dimension_2 = models.FloatField(default=0.0, verbose_name=_('Puntaje Dimensión 2 (Prácticas)'))
    total_score = models.FloatField(default=0.0, verbose_name=_('Puntaje Total Obtenido'))
    is_submitted = models.BooleanField(default=False, verbose_name=_('¿Enviado y Finalizado?'))

    class Meta:
        verbose_name = _('Evaluación de Estudiante')
        verbose_name_plural = _('Evaluaciones de Estudiantes')
        unique_together = ('student', 'assessment_type')
        ordering = ['-completed_at', '-started_at']

    def __str__(self):
        return f"{self.student.student_code} - {self.get_assessment_type_display()} (Total: {self.total_score})"

    def calculate_scores(self):
        """Calculates dimension subscores and overall score based on responses."""
        dim1_score = 0.0
        dim2_score = 0.0

        responses = self.responses.select_related('question__dimension', 'selected_option')
        for resp in responses:
            dim_code = resp.question.dimension.code
            score = resp.score_obtained
            if '1' in dim_code or 'KNOWLEDGE' in dim_code:
                dim1_score += score
            elif '2' in dim_code or 'PRACTICE' in dim_code:
                dim2_score += score
            else:
                dim1_score += score

        self.score_dimension_1 = round(dim1_score, 2)
        self.score_dimension_2 = round(dim2_score, 2)
        self.total_score = round(dim1_score + dim2_score, 2)
        self.completed_at = timezone.now()
        self.is_submitted = True
        self.save()

class StudentResponse(models.Model):
    """
    Individual response per question submitted by a student.
    """
    student_assessment = models.ForeignKey(
        StudentAssessment,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name=_('Evaluación')
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='student_responses',
        verbose_name=_('Pregunta')
    )
    selected_option = models.ForeignKey(
        AnswerOption,
        on_delete=models.CASCADE,
        related_name='selected_by',
        verbose_name=_('Opción Seleccionada')
    )
    score_obtained = models.FloatField(default=0.0, verbose_name=_('Puntaje Obtenido'))
    answered_at = models.DateTimeField(default=timezone.now, verbose_name=_('Hora de Respuesta'))

    class Meta:
        verbose_name = _('Respuesta de Estudiante')
        verbose_name_plural = _('Respuestas de Estudiantes')
        unique_together = ('student_assessment', 'question')

    def __str__(self):
        return f"{self.student_assessment.student.student_code} -> Q{self.question.id}: {self.score_obtained} pts"

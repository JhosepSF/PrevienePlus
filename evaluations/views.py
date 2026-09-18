from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from evaluations.models import Assessment, AssessmentType, Question, AnswerOption, StudentAssessment, StudentResponse
from accounts.models import StudyStage

@login_required
def take_assessment_view(request, assessment_type):
    """
    Renders and processes the Pretest or Postest evaluation.
    Enforces flow permissions, records timestamps, and locks evaluation upon submission.
    """
    if not hasattr(request.user, 'student_profile'):
        return redirect('research:dashboard')

    profile = request.user.student_profile
    assessment_type_upper = assessment_type.upper()

    if assessment_type_upper not in [AssessmentType.PRETEST, AssessmentType.POSTEST]:
        messages.error(request, "Tipo de evaluación inválido.")
        return redirect('accounts:dashboard')

    # Security check: Check consent
    if not profile.consent_given:
        messages.warning(request, "Debes leer y aceptar el asentimiento informado antes de continuar.")
        return redirect('accounts:consent')

    # Stage restrictions check
    if assessment_type_upper == AssessmentType.PRETEST:
        if not profile.can_access_pretest():
            messages.error(request, "Aún no tienes habilitado el Pretest.")
            return redirect('accounts:dashboard')
    elif assessment_type_upper == AssessmentType.POSTEST:
        if not profile.can_access_postest():
            messages.error(request, "El Postest se encuentra bloqueado hasta completar las actividades previas.")
            return redirect('accounts:dashboard')

    assessment = get_object_or_404(Assessment, assessment_type=assessment_type_upper, is_active=True)

    # Check if student has already completed this assessment
    existing_submission = StudentAssessment.objects.filter(
        student=profile,
        assessment_type=assessment_type_upper,
        is_submitted=True
    ).first()

    if existing_submission:
        messages.info(request, f"Ya has completado el {assessment.get_assessment_type_display()}. No es posible modificar tus respuestas.")
        return redirect('evaluations:summary', assessment_type=assessment_type.lower())

    # Get or create active in-progress assessment attempt
    student_assessment, created = StudentAssessment.objects.get_or_create(
        student=profile,
        assessment=assessment,
        assessment_type=assessment_type_upper,
        defaults={'started_at': timezone.now()}
    )

    questions = Question.objects.filter(
        assessment=assessment,
        is_active=True
    ).prefetch_related('options').select_related('dimension').order_by('order', 'id')

    if request.method == 'POST':
        # Process answers
        total_questions_count = questions.count()
        answered_count = 0

        for question in questions:
            field_name = f"question_{question.id}"
            selected_option_id = request.POST.get(field_name)
            
            if selected_option_id:
                try:
                    option = question.options.get(id=selected_option_id)
                    StudentResponse.objects.update_or_create(
                        student_assessment=student_assessment,
                        question=question,
                        defaults={
                            'selected_option': option,
                            'score_obtained': option.score_value,
                            'answered_at': timezone.now()
                        }
                    )
                    answered_count += 1
                except AnswerOption.DoesNotExist:
                    pass

        if answered_count < total_questions_count:
            messages.warning(request, f"Por favor, responde todas las preguntas antes de enviar ({answered_count} de {total_questions_count} respondidas).")
        else:
            # Complete and compute scores
            student_assessment.calculate_scores()

            # Advance student stage
            if assessment_type_upper == AssessmentType.PRETEST:
                profile.advance_stage_after_pretest()
                messages.success(request, "¡Pretest completado exitosamente! Ahora puedes continuar con la siguiente etapa.")
            else:
                profile.complete_postest()
                messages.success(request, "¡Postest completado exitosamente! Has finalizado tu participación en el estudio.")

            return redirect('evaluations:summary', assessment_type=assessment_type.lower())

    # Map existing responses if student is in progress
    existing_responses = {
        resp.question_id: resp.selected_option_id
        for resp in student_assessment.responses.all()
    }

    context = {
        'profile': profile,
        'assessment': assessment,
        'questions': questions,
        'total_questions': questions.count(),
        'existing_responses': existing_responses,
        'assessment_type': assessment_type.lower(),
    }
    return render(request, 'evaluations/take_assessment.html', context)

@login_required
def assessment_summary_view(request, assessment_type):
    """
    Shows a reassuring confirmation screen after finishing pretest or postest.
    """
    if not hasattr(request.user, 'student_profile'):
        return redirect('research:dashboard')

    profile = request.user.student_profile
    assessment_type_upper = assessment_type.upper()

    submission = get_object_or_404(
        StudentAssessment,
        student=profile,
        assessment_type=assessment_type_upper,
        is_submitted=True
    )

    context = {
        'profile': profile,
        'submission': submission,
        'assessment_type': assessment_type.lower(),
        'is_pretest': assessment_type_upper == AssessmentType.PRETEST,
        'is_postest': assessment_type_upper == AssessmentType.POSTEST,
    }
    return render(request, 'evaluations/assessment_summary.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.utils import timezone
from accounts.models import User, StudentProfile, ResearchGroup, StudyStage, UserRole
from accounts.forms import StudentBatchCreateForm
from evaluations.models import StudentAssessment, AssessmentType
from chatbot.models import ChatSession, ChatMessage, MessageRole
from research.models import ResearchSetting, ExportAuditLog
from research.services.export_service import export_participants_data, export_evaluations_data, export_chatbot_usage_data

def is_researcher(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or user.role in [UserRole.ADMIN, UserRole.RESEARCHER])

@login_required
@user_passes_test(is_researcher, login_url='accounts:login')
def dashboard_view(request):
    """
    Principal Research & Statistical Indicators Dashboard.
    Provides real-time descriptive statistics on quasi-experimental groups,
    evaluations progression, deltas, and Previene+ chatbot engagement.
    """
    settings_obj = ResearchSetting.get_settings()

    # Participant counts
    total_students = StudentProfile.objects.count()
    exp_students = StudentProfile.objects.filter(group=ResearchGroup.EXPERIMENTAL).count()
    ctr_students = StudentProfile.objects.filter(group=ResearchGroup.CONTROL).count()

    # Pretest metrics
    pre_exp = StudentAssessment.objects.filter(
        student__group=ResearchGroup.EXPERIMENTAL,
        assessment_type=AssessmentType.PRETEST,
        is_submitted=True
    )
    pre_ctr = StudentAssessment.objects.filter(
        student__group=ResearchGroup.CONTROL,
        assessment_type=AssessmentType.PRETEST,
        is_submitted=True
    )

    pre_exp_count = pre_exp.count()
    pre_ctr_count = pre_ctr.count()
    pre_total_count = pre_exp_count + pre_ctr_count

    pre_exp_avg = pre_exp.aggregate(
        tot=Avg('total_score'), d1=Avg('score_dimension_1'), d2=Avg('score_dimension_2')
    )
    pre_ctr_avg = pre_ctr.aggregate(
        tot=Avg('total_score'), d1=Avg('score_dimension_1'), d2=Avg('score_dimension_2')
    )

    # Postest metrics
    post_exp = StudentAssessment.objects.filter(
        student__group=ResearchGroup.EXPERIMENTAL,
        assessment_type=AssessmentType.POSTEST,
        is_submitted=True
    )
    post_ctr = StudentAssessment.objects.filter(
        student__group=ResearchGroup.CONTROL,
        assessment_type=AssessmentType.POSTEST,
        is_submitted=True
    )

    post_exp_count = post_exp.count()
    post_ctr_count = post_ctr.count()
    post_total_count = post_exp_count + post_ctr_count

    post_exp_avg = post_exp.aggregate(
        tot=Avg('total_score'), d1=Avg('score_dimension_1'), d2=Avg('score_dimension_2')
    )
    post_ctr_avg = post_ctr.aggregate(
        tot=Avg('total_score'), d1=Avg('score_dimension_1'), d2=Avg('score_dimension_2')
    )

    # Deltas calculation (Postest - Pretest)
    delta_exp_tot = (post_exp_avg['tot'] or 0) - (pre_exp_avg['tot'] or 0) if (post_exp_avg['tot'] and pre_exp_avg['tot']) else 0.0
    delta_ctr_tot = (post_ctr_avg['tot'] or 0) - (pre_ctr_avg['tot'] or 0) if (post_ctr_avg['tot'] and pre_ctr_avg['tot']) else 0.0

    # Chatbot metrics
    total_chat_sessions = ChatSession.objects.count()
    total_user_questions = ChatMessage.objects.filter(role=MessageRole.USER).count()
    avg_questions_per_user = round(total_user_questions / max(1, exp_students), 1)

    # Topics frequency
    all_msgs = ChatMessage.objects.filter(role=MessageRole.ASSISTANT).exclude(topics_detected='')
    topic_counts = {}
    for msg in all_msgs:
        for t in msg.topics_detected.split(','):
            topic = t.strip()
            if topic:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:6]

    # Recent participants
    recent_students = StudentProfile.objects.select_related('user').prefetch_related('student_assessments').all().order_by('-created_at')[:12]

    # Batch creation form
    batch_form = StudentBatchCreateForm()

    context = {
        'settings': settings_obj,
        'total_students': total_students,
        'exp_students': exp_students,
        'ctr_students': ctr_students,
        'pre_total_count': pre_total_count,
        'pre_exp_count': pre_exp_count,
        'pre_ctr_count': pre_ctr_count,
        'pre_exp_avg': pre_exp_avg,
        'pre_ctr_avg': pre_ctr_avg,
        'post_total_count': post_total_count,
        'post_exp_count': post_exp_count,
        'post_ctr_count': post_ctr_count,
        'post_exp_avg': post_exp_avg,
        'post_ctr_avg': post_ctr_avg,
        'delta_exp_tot': round(delta_exp_tot, 2),
        'delta_ctr_tot': round(delta_ctr_tot, 2),
        'total_chat_sessions': total_chat_sessions,
        'total_user_questions': total_user_questions,
        'avg_questions_per_user': avg_questions_per_user,
        'top_topics': sorted_topics,
        'recent_students': recent_students,
        'batch_form': batch_form,
    }
    return render(request, 'research/dashboard.html', context)

@login_required
@user_passes_test(is_researcher, login_url='accounts:login')
def student_list_view(request):
    """
    Participant administration page with filters and code generation.
    """
    group_filter = request.GET.get('group', '')
    stage_filter = request.GET.get('stage', '')
    search_q = request.GET.get('q', '').strip()

    students = StudentProfile.objects.select_related('user').prefetch_related('student_assessments').all()

    if group_filter:
        students = students.filter(group=group_filter)
    if stage_filter:
        students = students.filter(stage=stage_filter)
    if search_q:
        students = students.filter(student_code__icontains=search_q)

    students = students.order_by('student_code')

    context = {
        'students': students,
        'group_filter': group_filter,
        'stage_filter': stage_filter,
        'search_q': search_q,
        'batch_form': StudentBatchCreateForm(),
    }
    return render(request, 'research/student_list.html', context)

@login_required
@user_passes_test(is_researcher, login_url='accounts:login')
def generate_students_view(request):
    """
    Generates batch of pseudonymized student codes for experimental or control group.
    """
    if request.method == 'POST':
        form = StudentBatchCreateForm(request.POST)
        if form.is_valid():
            group = form.cleaned_data['group']
            prefix = form.cleaned_data['prefix'].strip().upper()
            quantity = form.cleaned_data['quantity']
            start_number = form.cleaned_data['start_number']

            created_count = 0
            for i in range(start_number, start_number + quantity):
                code = f"{prefix}-{str(i).zfill(3)}"
                username = f"student_{code.lower().replace('-', '_')}"

                # Avoid duplicate code
                if StudentProfile.objects.filter(student_code=code).exists():
                    continue

                user, _ = User.objects.get_or_create(
                    username=username,
                    defaults={'role': UserRole.STUDENT, 'is_active': True}
                )
                StudentProfile.objects.create(
                    user=user,
                    student_code=code,
                    group=group,
                    stage=StudyStage.CONSENT,
                    is_active=True
                )
                created_count += 1

            messages.success(request, f"Se generaron exitosamente {created_count} códigos de estudiantes ({prefix}).")
        else:
            messages.error(request, "Error en los datos del formulario de generación.")

    return redirect('research:student_list')

@login_required
@user_passes_test(is_researcher, login_url='accounts:login')
def export_dataset_view(request, dataset, file_format):
    """
    Downloads research dataset in CSV or XLSX.
    """
    fmt = file_format.lower()
    if fmt not in ['csv', 'xlsx']:
        fmt = 'csv'

    dataset_lower = dataset.lower()
    if dataset_lower in ['participants', 'participantes']:
        return export_participants_data(file_format=fmt, researcher_user=request.user)
    elif dataset_lower in ['evaluations', 'evaluaciones']:
        return export_evaluations_data(file_format=fmt, researcher_user=request.user)
    elif dataset_lower in ['chatbot', 'uso_chatbot']:
        return export_chatbot_usage_data(file_format=fmt, researcher_user=request.user)
    else:
        messages.error(request, "Conjunto de datos de exportación no reconocido.")
        return redirect('research:dashboard')

@login_required
@user_passes_test(is_researcher, login_url='accounts:login')
def update_stage_settings_view(request):
    """
    Researcher can enable or disable experimental stages globally.
    """
    if request.method == 'POST':
        setting = ResearchSetting.get_settings()
        setting.pretest_stage_open = 'pretest_open' in request.POST
        setting.intervention_stage_open = 'intervention_open' in request.POST
        setting.postest_stage_open = 'postest_open' in request.POST
        setting.save()
        messages.success(request, "Configuración de etapas actualizada correctamente.")
    return redirect('research:dashboard')

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from accounts.forms import StudentLoginForm, ResearcherLoginForm
from accounts.models import StudyStage, UserRole

def login_view(request):
    """
    Unified entry point: Primary tab for Students (pseudonymized code) and secondary tab for Researchers.
    """
    if request.user.is_authenticated:
        if hasattr(request.user, 'student_profile'):
            return redirect('accounts:dashboard')
        return redirect('research:dashboard')

    student_form = StudentLoginForm()
    researcher_form = ResearcherLoginForm()
    active_tab = 'student'

    if request.method == 'POST':
        action = request.POST.get('action', 'student_login')
        
        if action == 'student_login':
            student_form = StudentLoginForm(request.POST)
            if student_form.is_valid():
                code = student_form.cleaned_data['student_code']
                user = authenticate(request, student_code=code)
                if user is not None:
                    login(request, user)
                    messages.success(request, f"¡Bienvenido! Has ingresado con el código {code}.")
                    # Check if consent is needed
                    profile = user.student_profile
                    if not profile.consent_given:
                        return redirect('accounts:consent')
                    return redirect('accounts:dashboard')
                else:
                    messages.error(request, f"El código '{code}' no fue encontrado o está inactivo. Verifica con el investigador.")
            active_tab = 'student'

        elif action == 'researcher_login':
            researcher_form = ResearcherLoginForm(request.POST)
            if researcher_form.is_valid():
                username = researcher_form.cleaned_data['username']
                password = researcher_form.cleaned_data['password']
                user = authenticate(request, username=username, password=password)
                if user is not None and (user.is_staff or user.is_superuser or user.role in [UserRole.ADMIN, UserRole.RESEARCHER]):
                    login(request, user)
                    messages.success(request, f"Sesión iniciada como investigador ({user.username}).")
                    return redirect('research:dashboard')
                else:
                    messages.error(request, "Credenciales de investigador incorrectas o sin permisos administrativos.")
            active_tab = 'researcher'

    context = {
        'student_form': student_form,
        'researcher_form': researcher_form,
        'active_tab': active_tab,
    }
    return render(request, 'accounts/login.html', context)

@login_required
def consent_view(request):
    """
    Informed Assent / Consent view for school participants in the research study.
    Explains the objective, voluntary nature, privacy protection, and instructions.
    """
    if not hasattr(request.user, 'student_profile'):
        return redirect('research:dashboard')

    profile = request.user.student_profile

    if request.method == 'POST':
        action = request.POST.get('consent_action')
        if action == 'accept':
            profile.consent_given = True
            profile.consent_timestamp = timezone.now()
            if profile.stage == StudyStage.CONSENT:
                profile.stage = StudyStage.PRETEST
            profile.save()
            messages.success(request, "¡Gracias! Tu participación ha sido confirmada con éxito.")
            return redirect('accounts:dashboard')
        elif action == 'decline':
            messages.warning(request, "Has decidido no participar. Puedes cerrar esta ventana o comunicarte con tu docente.")
            return redirect('accounts:logout')

    context = {
        'profile': profile,
    }
    return render(request, 'accounts/consent.html', context)

@login_required
def dashboard_view(request):
    """
    Student dashboard displaying experimental progression, current phase status,
    and action triggers for Pretest, Intervention (Previene+), and Postest.
    """
    if not hasattr(request.user, 'student_profile'):
        return redirect('research:dashboard')

    profile = request.user.student_profile

    if not profile.consent_given:
        return redirect('accounts:consent')

    # Get evaluation statuses if evaluations app is loaded
    pretest_assessment = getattr(profile, 'student_assessments', None)
    pretest_done = False
    postest_done = False

    if pretest_assessment is not None:
        pretest_done = profile.student_assessments.filter(assessment_type='PRETEST', is_submitted=True).exists()
        postest_done = profile.student_assessments.filter(assessment_type='POSTEST', is_submitted=True).exists()

    context = {
        'profile': profile,
        'pretest_done': pretest_done,
        'postest_done': postest_done,
    }
    return render(request, 'accounts/dashboard.html', context)

def logout_view(request):
    """Logs out user and redirects to login."""
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('accounts:login')

from django.conf import settings

def student_context(request):
    """
    Context processor to make student profile and research application metadata
    available across all Django templates.
    """
    context = {
        'CHATBOT_NAME': getattr(settings, 'CHATBOT_NAME', 'Previene+'),
        'CHATBOT_VERSION': getattr(settings, 'CHATBOT_VERSION', '1.0.0-research'),
        'INSTITUTION_NAME': getattr(settings, 'INSTITUTION_NAME', 'I.E. Investigación Prevención ITS'),
        'student_profile': None,
        'is_student': False,
        'is_researcher': False,
    }

    if request.user.is_authenticated:
        if hasattr(request.user, 'student_profile'):
            context['student_profile'] = request.user.student_profile
            context['is_student'] = True
        elif request.user.is_staff or request.user.is_superuser or getattr(request.user, 'role', '') in ['ADMIN', 'RESEARCHER']:
            context['is_researcher'] = True

    return context

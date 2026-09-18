import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.views.decorators.http import require_POST
from accounts.models import StudyStage
from chatbot.models import ChatSession, ChatMessage, InterventionConfigLog, MessageRole
from chatbot.services.ai_service import AIService
from knowledge.models import KnowledgeChunk

@login_required
def chat_view(request):
    """
    Main educational chat interface for Previene+.
    Strictly restricted to Experimental Group participants who have completed the Pretest.
    """
    if not hasattr(request.user, 'student_profile'):
        return redirect('research:dashboard')

    profile = request.user.student_profile

    # Gating checks
    if not profile.is_experimental:
        messages.warning(request, "El asistente Previene+ está asignado a la intervención del grupo experimental.")
        return redirect('accounts:dashboard')

    if not profile.can_access_intervention():
        messages.error(request, "Debes completar el Pretest antes de interactuar con el asistente Previene+.")
        return redirect('accounts:dashboard')

    # Get or create active chat session
    chat_session, created = ChatSession.objects.get_or_create(
        student=profile,
        is_active=True,
        defaults={'started_at': timezone.now()}
    )

    # If new session, create initial welcoming system/assistant greeting
    if created or chat_session.messages.count() == 0:
        welcome_text = (
            "¡Hola! 👋 Soy **Previene+**, tu asistente educativo con inteligencia artificial creado para "
            "ayudarte a aprender sobre prevención y cuidado frente a infecciones de transmisión sexual (ITS).\n\n"
            "Puedes hacerme preguntas con total confianza sobre:\n"
            "• ¿Qué son las ITS y cómo se transmiten?\n"
            "• Formas efectivas de prevención y uso correcto del preservativo.\n"
            "• VIH, VPH, sífilis, gonorrea, herpes y hepatitis.\n"
            "• Mitos frecuentes y verdades científicas.\n"
            "• ¿Dónde acceder a pruebas gratuitas y orientación de salud?\n\n"
            "¿Qué tema te gustaría consultar hoy?"
        )
        ChatMessage.objects.create(
            session=chat_session,
            role=MessageRole.ASSISTANT,
            content=welcome_text,
            sources_used="MINSA Perú / OPS / OMS - Guías de Prevención de ITS",
            topics_detected="Bienvenida, Concepto de ITS, Prevención",
            tokens_used=0
        )
        chat_session.update_activity()

    chat_messages = chat_session.messages.all().order_by('created_at')

    # Suggested educational prompts for adolescents
    suggested_prompts = [
        "¿Cuáles son las formas más comunes de transmisión de las ITS?",
        "¿Cómo se usa correctamente un preservativo y qué tan seguro es?",
        "¿Qué es el Virus del Papiloma Humano (VPH) y cómo se previene?",
        "¿El VIH es lo mismo que el SIDA? ¿Cómo se detecta?",
        "¿Es verdad que una persona con una ITS siempre tiene síntomas?",
        "¿A dónde puedo acudir si necesito orientación o una prueba gratuita?",
    ]

    context = {
        'profile': profile,
        'chat_session': chat_session,
        'chat_messages': chat_messages,
        'suggested_prompts': suggested_prompts,
        'message_count': chat_session.messages.filter(role=MessageRole.USER).count(),
        'min_messages_recommended': 3,
    }
    return render(request, 'chatbot/chat.html', context)

@login_required
@require_POST
def send_message_api(request):
    """
    API endpoint for sending a message and getting the AI RAG response.
    Supports standard JSON requests and HTMX requests.
    """
    if not hasattr(request.user, 'student_profile'):
        return JsonResponse({'error': 'No autorizado.'}, status=403)

    profile = request.user.student_profile
    if not profile.is_experimental or not profile.can_access_intervention():
        return JsonResponse({'error': 'Acceso no permitido a la intervención.'}, status=403)

    # Parse request data
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            user_text = data.get('message', '').strip()
        except Exception:
            return JsonResponse({'error': 'Formato JSON inválido.'}, status=400)
    else:
        user_text = request.POST.get('message', '').strip()

    if not user_text:
        return JsonResponse({'error': 'El mensaje no puede estar vacío.'}, status=400)

    # Get active session
    chat_session = ChatSession.objects.filter(student=profile, is_active=True).first()
    if not chat_session:
        chat_session = ChatSession.objects.create(student=profile, started_at=timezone.now())

    # Build history context
    recent_msgs = chat_session.messages.all().order_by('-created_at')[:6]
    history_payload = []
    for msg in reversed(recent_msgs):
        history_payload.append({
            'role': msg.role,
            'content': msg.content
        })

    # Save user message
    enable_full_logging = getattr(settings, 'ENABLE_FULL_MESSAGE_LOGGING', True)
    stored_user_text = user_text if enable_full_logging else "[Contenido protegido por política de privacidad]"

    user_msg_obj = ChatMessage.objects.create(
        session=chat_session,
        role=MessageRole.USER,
        content=stored_user_text,
    )

    # Call AI RAG Service
    ai_result = AIService.generate_response(user_text, history_payload)

    # Save assistant message
    assistant_msg_obj = ChatMessage.objects.create(
        session=chat_session,
        role=MessageRole.ASSISTANT,
        content=ai_result['content'],
        sources_used="; ".join(ai_result['sources']),
        topics_detected=", ".join(ai_result['topics']),
        tokens_used=ai_result.get('tokens', 0)
    )

    # Log scientific reproducibility entry
    chunks_count = KnowledgeChunk.objects.filter(is_active=True).count()
    InterventionConfigLog.objects.create(
        student=profile,
        session=chat_session,
        app_version=getattr(settings, 'CHATBOT_VERSION', '1.0.0-research'),
        model_name=ai_result.get('model', 'gpt-5.6-luna'),
        temperature=0.3,
        system_prompt_version=ai_result.get('prompt_version', 'v1.0-research-safe'),
        system_prompt_text=ai_result.get('system_prompt_text', ''),
        knowledge_chunks_count=chunks_count,
        recorded_at=timezone.now()
    )

    # Update session metrics
    chat_session.update_activity()

    return JsonResponse({
        'success': True,
        'user_message': {
            'content': user_text,
            'created_at': user_msg_obj.created_at.strftime('%H:%M'),
        },
        'assistant_message': {
            'content': assistant_msg_obj.content,
            'sources': ai_result['sources'],
            'topics': ai_result['topics'],
            'created_at': assistant_msg_obj.created_at.strftime('%H:%M'),
        },
        'total_user_messages': chat_session.messages.filter(role=MessageRole.USER).count(),
    })

@login_required
@require_POST
def finish_intervention_view(request):
    """
    Student indicates completion of their educational intervention with Previene+,
    moving the student to the Postest stage.
    """
    if not hasattr(request.user, 'student_profile'):
        return redirect('research:dashboard')

    profile = request.user.student_profile
    if not profile.is_experimental:
        return redirect('accounts:dashboard')

    chat_session = ChatSession.objects.filter(student=profile, is_active=True).first()
    if chat_session:
        chat_session.is_active = False
        chat_session.ended_at = timezone.now()
        chat_session.update_activity()

    profile.complete_intervention()
    messages.success(request, "¡Excelente! Has completado la intervención con Previene+. Ahora puedes acceder al Postest.")
    return redirect('accounts:dashboard')

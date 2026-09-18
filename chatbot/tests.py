from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, StudentProfile, ResearchGroup, StudyStage, UserRole
from knowledge.models import KnowledgeCategory, KnowledgeDocument, KnowledgeChunk
from chatbot.models import ChatSession, ChatMessage, InterventionConfigLog
from chatbot.services.rag_retriever import retrieve_relevant_chunks
from chatbot.services.ai_service import AIService

class ChatbotTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Knowledge Base Setup
        self.cat_vih = KnowledgeCategory.objects.create(name='VIH y SIDA', code='vih-sida')
        self.doc_vih = KnowledgeDocument.objects.create(
            category=self.cat_vih,
            title='Información Preventiva del VIH',
            source_institution='OPS/OMS',
            publication_year=2024,
            full_content='El VIH se transmite por relaciones sexuales sin proteccion y por via sanguinea. El uso correcto del condon previene el contagio.',
            is_active=True
        )

        # Experimental student ready for intervention
        self.user_exp = User.objects.create_user(username='student_exp_201', role=UserRole.STUDENT)
        self.profile_exp = StudentProfile.objects.create(
            user=self.user_exp,
            student_code='EXP-201',
            group=ResearchGroup.EXPERIMENTAL,
            stage=StudyStage.INTERVENTION,
            consent_given=True,
            is_active=True
        )

        # Control student
        self.user_ctr = User.objects.create_user(username='student_ctr_201', role=UserRole.STUDENT)
        self.profile_ctr = StudentProfile.objects.create(
            user=self.user_ctr,
            student_code='CTR-201',
            group=ResearchGroup.CONTROL,
            stage=StudyStage.POSTEST,
            consent_given=True,
            is_active=True
        )

    def test_rag_retrieval(self):
        chunks = retrieve_relevant_chunks("¿Cómo se previene el VIH?", top_k=2)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertIn('VIH', chunks[0]['chunk_text'])

    def test_ai_service_simulation_response(self):
        result = AIService.generate_response("¿Cómo se contagia el VIH?")
        self.assertTrue(result['success'])
        self.assertIn('VIH y SIDA', result['topics'])
        self.assertIn('OPS/OMS', result['sources'][0])

    def test_experimental_student_can_chat(self):
        self.client.force_login(self.user_exp)
        response = self.client.get(reverse('chatbot:chat'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Previene+")

    def test_control_student_blocked_from_chatbot(self):
        self.client.force_login(self.user_ctr)
        response = self.client.get(reverse('chatbot:chat'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:dashboard'))

    def test_send_message_api_records_log_and_metrics(self):
        self.client.force_login(self.user_exp)
        response = self.client.post(
            reverse('chatbot:send_message'),
            data={'message': '¿Qué es el VIH?'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        # Check session & reproducibility log created
        session = ChatSession.objects.filter(student=self.profile_exp).first()
        self.assertIsNotNone(session)
        self.assertGreater(session.messages.count(), 0)

        log = InterventionConfigLog.objects.filter(student=self.profile_exp).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.system_prompt_version, 'v1.0-research-safe')

    @patch('openai.OpenAI')
    def test_openai_api_mock_integration(self, mock_openai_class):
        # Mock client response
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_completion = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Respuesta mockeada de IA sobre prevención de ITS."
        mock_completion.choices = [mock_choice]
        mock_completion.usage.total_tokens = 45
        mock_client.chat.completions.create.return_value = mock_completion

        with patch('django.conf.settings.OPENAI_API_KEY', 'sk-test-mock-key-12345'):
            result = AIService.generate_response("¿Cómo me protejo del VIH?")
            self.assertTrue(result['success'])
            self.assertEqual(result['content'], "Respuesta mockeada de IA sobre prevención de ITS.")
            self.assertEqual(result['tokens'], 45)

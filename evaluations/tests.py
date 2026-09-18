from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, StudentProfile, ResearchGroup, StudyStage, UserRole
from evaluations.models import Dimension, Assessment, AssessmentType, Question, QuestionType, AnswerOption, StudentAssessment

class EvaluationsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='student_exp_101', role=UserRole.STUDENT)
        self.profile = StudentProfile.objects.create(
            user=self.user,
            student_code='EXP-101',
            group=ResearchGroup.EXPERIMENTAL,
            stage=StudyStage.PRETEST,
            consent_given=True,
            consent_timestamp=timezone.now(),
            is_active=True
        )

        self.dim1 = Dimension.objects.create(code='DIM_1_KNOWLEDGE', name='Dimensión 1: Conocimientos', order=1)
        self.dim2 = Dimension.objects.create(code='DIM_2_PRACTICE', name='Dimensión 2: Prácticas', order=2)

        self.assessment = Assessment.objects.create(
            assessment_type=AssessmentType.PRETEST,
            title='Pretest de Evaluación',
            instructions='Instrucciones de prueba',
            is_active=True
        )

        # Q1 Dim1
        self.q1 = Question.objects.create(
            assessment=self.assessment,
            dimension=self.dim1,
            question_text='¿El preservativo previene el VIH?',
            question_type=QuestionType.TRUE_FALSE,
            weight=1.0,
            order=1
        )
        self.opt1_correct = AnswerOption.objects.create(question=self.q1, option_text='Verdadero', score_value=1.0, is_correct=True, order=1)
        self.opt1_wrong = AnswerOption.objects.create(question=self.q1, option_text='Falso', score_value=0.0, is_correct=False, order=2)

        # Q2 Dim2
        self.q2 = Question.objects.create(
            assessment=self.assessment,
            dimension=self.dim2,
            question_text='¿Verificas la fecha de vencimiento?',
            question_type=QuestionType.LIKERT,
            weight=1.0,
            order=2
        )
        self.opt2_correct = AnswerOption.objects.create(question=self.q2, option_text='Siempre', score_value=1.0, is_correct=True, order=1)

    def test_take_assessment_flow_and_score_calculation(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('evaluations:take_assessment', kwargs={'assessment_type': 'pretest'}), {
            f'question_{self.q1.id}': self.opt1_correct.id,
            f'question_{self.q2.id}': self.opt2_correct.id,
        })
        self.assertEqual(response.status_code, 302)

        submission = StudentAssessment.objects.get(student=self.profile, assessment_type=AssessmentType.PRETEST)
        self.assertTrue(submission.is_submitted)
        self.assertEqual(submission.score_dimension_1, 1.0)
        self.assertEqual(submission.score_dimension_2, 1.0)
        self.assertEqual(submission.total_score, 2.0)

        # Verify progression: Experimental moves to INTERVENTION
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.stage, StudyStage.INTERVENTION)

    def test_cannot_retake_submitted_assessment(self):
        self.client.force_login(self.user)
        # Create completed submission
        StudentAssessment.objects.create(
            student=self.profile,
            assessment=self.assessment,
            assessment_type=AssessmentType.PRETEST,
            total_score=2.0,
            is_submitted=True
        )

        response = self.client.get(reverse('evaluations:take_assessment', kwargs={'assessment_type': 'pretest'}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('evaluations:summary', kwargs={'assessment_type': 'pretest'}))

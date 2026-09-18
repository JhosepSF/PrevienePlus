from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, StudentProfile, ResearchGroup, StudyStage, UserRole

class AccountsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_exp = User.objects.create_user(username='student_exp_001', role=UserRole.STUDENT)
        self.profile_exp = StudentProfile.objects.create(
            user=self.user_exp,
            student_code='EXP-001',
            group=ResearchGroup.EXPERIMENTAL,
            stage=StudyStage.CONSENT,
            consent_given=False,
            is_active=True
        )

        self.user_ctr = User.objects.create_user(username='student_ctr_001', role=UserRole.STUDENT)
        self.profile_ctr = StudentProfile.objects.create(
            user=self.user_ctr,
            student_code='CTR-001',
            group=ResearchGroup.CONTROL,
            stage=StudyStage.PRETEST,
            consent_given=True,
            is_active=True
        )

        self.admin = User.objects.create_superuser(username='admin_test', password='password123', email='admin@test.pe', role=UserRole.ADMIN)

    def test_student_login_with_code(self):
        response = self.client.post(reverse('accounts:login'), {
            'action': 'student_login',
            'student_code': 'EXP-001'
        })
        self.assertEqual(response.status_code, 302)
        # Should redirect to consent since consent_given is False
        self.assertRedirects(response, reverse('accounts:consent'))

    def test_invalid_student_code(self):
        response = self.client.post(reverse('accounts:login'), {
            'action': 'student_login',
            'student_code': 'NON-EXISTENT-CODE'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no fue encontrado o está inactivo")

    def test_consent_flow(self):
        self.client.force_login(self.user_exp)
        response = self.client.post(reverse('accounts:consent'), {
            'consent_action': 'accept'
        })
        self.assertEqual(response.status_code, 302)
        self.profile_exp.refresh_from_db()
        self.assertTrue(self.profile_exp.consent_given)
        self.assertEqual(self.profile_exp.stage, StudyStage.PRETEST)

    def test_researcher_login(self):
        response = self.client.post(reverse('accounts:login'), {
            'action': 'researcher_login',
            'username': 'admin_test',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('research:dashboard'))

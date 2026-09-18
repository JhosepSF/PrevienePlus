from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, StudentProfile, ResearchGroup, StudyStage, UserRole
from research.models import ResearchSetting, ExportAuditLog

class ResearchTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.researcher = User.objects.create_superuser(username='prof_investigador', password='password123', email='prof@investigacion.edu.pe', role=UserRole.RESEARCHER)
        
        self.student_user = User.objects.create_user(username='student_anon', role=UserRole.STUDENT)
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            student_code='EXP-301',
            group=ResearchGroup.EXPERIMENTAL,
            stage=StudyStage.PRETEST,
            consent_given=True,
            is_active=True
        )

    def test_student_cannot_access_research_dashboard(self):
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('research:dashboard'))
        # Should redirect to login / dashboard
        self.assertEqual(response.status_code, 302)

    def test_researcher_can_access_dashboard(self):
        self.client.force_login(self.researcher)
        response = self.client.get(reverse('research:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Panel de Control del Investigador")

    def test_export_evaluations_csv(self):
        self.client.force_login(self.researcher)
        response = self.client.get(reverse('research:export_dataset', kwargs={'dataset': 'evaluaciones', 'file_format': 'csv'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment; filename=', response['Content-Disposition'])
        self.assertTrue(ExportAuditLog.objects.filter(dataset_type='EVALUATIONS').exists())

    def test_export_evaluations_xlsx(self):
        self.client.force_login(self.researcher)
        response = self.client.get(reverse('research:export_dataset', kwargs={'dataset': 'evaluaciones', 'file_format': 'xlsx'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_batch_generate_students(self):
        self.client.force_login(self.researcher)
        response = self.client.post(reverse('research:generate_students'), {
            'group': ResearchGroup.EXPERIMENTAL,
            'prefix': 'TESTEXP',
            'quantity': 5,
            'start_number': 1
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StudentProfile.objects.filter(student_code__startswith='TESTEXP').count(), 5)

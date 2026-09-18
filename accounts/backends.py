from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from accounts.models import StudentProfile

User = get_user_model()

class PseudonymizedStudentBackend(BaseBackend):
    """
    Custom authentication backend allowing students to log in exclusively using their pseudonymized code.
    """
    def authenticate(self, request, student_code=None, **kwargs):
        if not student_code:
            return None
        
        normalized_code = str(student_code).strip().upper()
        try:
            profile = StudentProfile.objects.select_related('user').get(
                student_code__iexact=normalized_code,
                is_active=True
            )
            return profile.user
        except StudentProfile.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

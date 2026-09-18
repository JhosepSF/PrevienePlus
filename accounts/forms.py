from django import forms
from django.utils.translation import gettext_lazy as _
from accounts.models import StudentProfile, ResearchGroup

class StudentLoginForm(forms.Form):
    """
    Minimalist student login form with a single pseudonymized code field.
    """
    student_code = forms.CharField(
        max_length=30,
        required=True,
        label=_("Código de Estudiante"),
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center fw-bold letter-spacing-1',
            'placeholder': 'Ej. EXP-001 o CTR-001',
            'autocomplete': 'off',
            'autofocus': True,
            'id': 'student_code_input'
        })
    )

    def clean_student_code(self):
        code = self.cleaned_data.get('student_code', '').strip().upper()
        if not code:
            raise forms.ValidationError(_("Por favor, ingresa tu código asignado."))
        return code

class ResearcherLoginForm(forms.Form):
    """
    Standard researcher / administrator login form.
    """
    username = forms.CharField(
        max_length=150,
        required=True,
        label=_("Usuario / Investigador"),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de usuario'
        })
    )
    password = forms.CharField(
        required=True,
        label=_("Contraseña"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••'
        })
    )

class StudentBatchCreateForm(forms.Form):
    """
    Form for researchers to batch-generate pseudonymized student codes.
    """
    group = forms.ChoiceField(
        choices=ResearchGroup.choices,
        label=_("Grupo de Investigación"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    prefix = forms.CharField(
        max_length=10,
        initial='EXP',
        label=_("Prefijo del Código"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. EXP o CTR'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        max_value=200,
        initial=20,
        label=_("Cantidad de Estudiantes a Generar"),
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    start_number = forms.IntegerField(
        min_value=1,
        initial=1,
        label=_("Número Inicial"),
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

from django.urls import path
from evaluations import views

app_name = 'evaluations'

urlpatterns = [
    path('<str:assessment_type>/', views.take_assessment_view, name='take_assessment'),
    path('<str:assessment_type>/summary/', views.assessment_summary_view, name='summary'),
]

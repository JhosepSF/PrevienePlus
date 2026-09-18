from django.urls import path
from research import views

app_name = 'research'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('students/', views.student_list_view, name='student_list'),
    path('students/generate/', views.generate_students_view, name='generate_students'),
    path('export/<str:dataset>/<str:file_format>/', views.export_dataset_view, name='export_dataset'),
    path('settings/stages/', views.update_stage_settings_view, name='update_stage_settings'),
]

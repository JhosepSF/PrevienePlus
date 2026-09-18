from django.urls import path
from knowledge import views

app_name = 'knowledge'

urlpatterns = [
    path('', views.knowledge_index_view, name='index'),
    path('doc/<int:doc_id>/', views.document_detail_view, name='document_detail'),
]

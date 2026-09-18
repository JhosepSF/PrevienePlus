from django.urls import path
from chatbot import views

app_name = 'chatbot'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('api/send/', views.send_message_api, name='send_message'),
    path('finish/', views.finish_intervention_view, name='finish_intervention'),
]

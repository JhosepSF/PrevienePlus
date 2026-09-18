"""
URL configuration for Previene+ project.
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('accounts:login'), name='root_redirect'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('evaluations/', include('evaluations.urls', namespace='evaluations')),
    path('chatbot/', include('chatbot.urls', namespace='chatbot')),
    path('knowledge/', include('knowledge.urls', namespace='knowledge')),
    path('research/', include('research.urls', namespace='research')),
]

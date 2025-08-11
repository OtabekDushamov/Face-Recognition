"""
URL configuration for the verify app.
"""

from django.urls import path
from . import views

app_name = 'verify'

urlpatterns = [
    # Main camera page
    path('', views.camera_view, name='camera'),
    
    # API endpoints
    path('api/verify/', views.FaceVerificationAPI.as_view(), name='api_verify'),
    path('api/staff/', views.staff_list_api, name='api_staff_list'),
    path('api/staff/<str:staff_id>/', views.staff_detail_api, name='api_staff_detail'),
    path('api/stats/', views.verification_stats_api, name='api_stats'),
    path('api/attempts/', views.verification_attempts_api, name='api_attempts_all'),
    path('api/attempts/<str:staff_id>/', views.verification_attempts_api, name='api_attempts_staff'),
    path('api/health/', views.health_check, name='api_health'),
]

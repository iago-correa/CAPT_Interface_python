from django.urls import path
from . import views

app_name = 'practice'

urlpatterns = [
    path('', views.practice, name='practice'),
    path('track/', views.track, name='track_activity')
]

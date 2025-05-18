from django.urls import path
from . import views

app_name = 'practice'

urlpatterns = [
    path('', views.practice, name='practice'),
]

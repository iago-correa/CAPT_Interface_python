from django.urls import path
from . import views

app_name = 'evaluate'

urlpatterns = [
    path('', views.evaluate, name='evaluate'),
]
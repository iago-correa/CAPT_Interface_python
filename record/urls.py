from django.urls import path
from . import views

app_name = 'record'

urlpatterns = [
    path('<int:t>/', views.record, name='record'),
]
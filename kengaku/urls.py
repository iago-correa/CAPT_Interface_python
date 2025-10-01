from django.urls import path
from . import views

app_name = 'kengaku'

urlpatterns = [
    path('', views.demo, name='demo'),
    path('demo/reset', views.reset, name='reset')
]
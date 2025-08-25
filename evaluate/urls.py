from django.urls import path
from . import views

app_name = 'evaluate'

urlpatterns = [
    path('', views.select_part, name='select_part'),
    path('part<int:part_number>/', views.evaluate, name='evaluate')
]
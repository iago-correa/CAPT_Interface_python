from django.urls import path
from . import views

app_name = 'login'

urlpatterns = [
    path('', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('evaluation/', views.evaluation_login, name='evaluation_login'),
    path('evaluation/logout', views.evaluation_logout, name='evaluation_logout')
]
from django.urls import path
from . import views

app_name = 'login'
urlpatterns = [
    path('', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    # Admin only
    path('sessions/<int:student_id>/', views.sessions_view, name='sessions')
]
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from login.forms import LogInStudent
from login.models import Student, Session
from .models import Activity, Audio

def practice(request):
    if request.session.get('student_id'):
        # student = Student.objects.get(student_id = request.session['student_id'])
        audio_list = {}
        audio_list['audio/test_audio.wav'] = "Audio test 1" 
        audio_list['audio/test_audio_2.wav'] = "Audio test 2" 
        return render(request, 'practice/practice.html', {'audio_list': audio_list, 'MEDIA_URL': settings.MEDIA_URL})
    else:
        login_form = LogInStudent()
        return render(request, 'login/login.html', {'login_form': login_form, 'error': 'サインインしてください。'})
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import urlencode
from login.forms import LogInStudent
from login.models import Student, Session
from login.utils import get_current_period, get_signed_url, get_period_of
from .models import Activity, Audio
from record.models import Recording
from random import shuffle
import json

def practice(request):

    session_id = request.session.get('session_id')
    if not session_id:
        error_message = 'サインインしてください。'
        query_params = urlencode({'error': error_message})
        return redirect(f"{reverse('login:login')}?{query_params}")
    
    try:
        session = Session.objects.get(id=session_id)
        student = session.student
    except Session.DoesNotExist:
        # Handle rare case where session_id is invalid
        request.session.flush() # Clear invalid session
        error_message = '無効なセッションです。再度サインインしてください。'
        query_params = urlencode({'error': error_message})
        return redirect(f"{reverse('login:login')}?{query_params}")
    
    page_current_period_check = get_current_period()

    if page_current_period_check != 1:

        message = '現在は練習期間外のため、アクセスできません。練習期間中に再度アクセスしてください。'
        query_params = urlencode({'error': message})
        return redirect(f"{reverse('login:logout')}?{query_params}")

    if request.session.get('student_id'):
        student = Student.objects.get(student_id = request.session['student_id'])
        session = Session.objects.get(id = request.session['session_id'])

        train_set = []

        if student.control_group: 
            reference_audios = Audio.objects.all().filter(type = "train_nat")
        else:
            reference_audios = Audio.objects.filter(type = "train_gs", student=student)
        
        for audio in reference_audios:
            recording = Recording.objects.filter(
                activities__session__student=student, 
                activities__type='train_record',
                original_audio = audio).order_by('activities__time').last()
            if recording:
                
                file_key = f"{settings.MEDIA_ROOT}{recording.recorded_audio.name}"
                recording_signed_url = get_signed_url(file_key)
                
                recording_time = Activity.objects.filter(recording=recording, type='train_record').order_by('-time').first().time
                if get_current_period() == get_period_of(recording_time):
                    checked = True
                else:
                    checked = False
                train_set.append([audio, recording, recording_signed_url, checked])
                
            else:
                train_set.append([audio, recording, None, False])
        shuffle(train_set)
        return render(request, 'practice/practice.html', {'train_set': train_set, 'MEDIA_URL': settings.MEDIA_URL})
    else:
        login_form = LogInStudent()
        return render(request, 'login/login.html', {'login_form': login_form, 'error': 'サインインしてください。'})
    
@csrf_exempt
def log_activity(request):
    if request.method == 'POST':
        session = Session.objects.get(id = request.session['session_id'])
        data = json.loads(request.body)
        activity_type = data.get('type')

        if activity_type == 'train_listen_ref':
            audio = Audio.objects.get(id=data.get('audio_source_id'))

            Activity.objects.create(
                session=session,
                audio=audio,
                type=activity_type,
                time=timezone.now()
            )

        elif activity_type == 'train_listen_own':
            recording = Recording.objects.get(id=data.get('audio_source_id'))

            Activity.objects.create(
                session=session,
                recording=recording,
                type=activity_type,
                time=timezone.now()
            )

        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'invalid request'}, status=400)
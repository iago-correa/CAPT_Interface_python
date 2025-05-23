from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from login.forms import LogInStudent
from login.models import Student, Session
from .models import Activity, Audio
from record.models import Recording
import json

def practice(request):

    if request.session.get('student_id'):
        student = Student.objects.get(student_id = request.session['student_id'])
        session = Session.objects.get(id = request.session['session_id'])

        if student.control_group: 
            
            reference_audios = Audio.objects.all().filter(type = "train_nat")
            recordings = Recording.objects.filter(
                activities__session__student=student, 
                activities__type='train_record',
                original_audio__in = reference_audios)

        else:
            
            reference_audios = Audio.objects.filter(type = "train_gs", student=student)
            recordings = Recording.objects.filter(
                activities__session__student=student, 
                activities__type='train_record',
                original_audio__in = reference_audios)
        
        train_set = []
        for audio in reference_audios:
            for recording in recordings:
                if recording.original_audio == audio:
                    train_set.append([audio, recording])
        
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
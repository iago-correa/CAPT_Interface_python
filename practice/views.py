from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from login.forms import LogInStudent
from login.models import Student, Session
from .models import Activity, Audio
from record.models import Recording

def practice(request):

    if request.session.get('student_id'):
        student = Student.objects.get(student_id = request.session['student_id'])
        
        training_set = {}

        if student.control_group: 
            
            reference_audios = Audio.objects.all().filter(type = "train_nat")
            recording_audios = Recording.objects.filter(
                original_audio__in=reference_audios
            )
            # Sort by activity.type.time, get the top 1
            
        else:
            
            reference_audio = Audio.objects.all().filter(type = "train_nat")
            reference_audio = Audio.objects.all().filter(type = "train_gs", student= student, )
        
        audio_list = {}
        for audio in reference_audios:
            audio_list[audio.file.url] = audio.transcript
        
        return render(request, 'practice/practice.html', {'audio_list': audio_list, 'MEDIA_URL': settings.MEDIA_URL})
    else:
        login_form = LogInStudent()
        return render(request, 'login/login.html', {'login_form': login_form, 'error': 'サインインしてください。'})
    
def track(request):
    if request.method == "POST":
        return HttpResponse(f"Pegou o post")
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.files import File
from django.shortcuts import render, redirect
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponse
from django.urls import reverse
from login.forms import LogInStudent
from pathlib import Path
from .models import Recording
from login.models import Session
from practice.models import Audio, Activity
from random import shuffle
from urllib.parse import urlencode
import datetime

def checkPeriod():

    pre_start_date = timezone.make_aware(datetime.datetime(2025, 5, 27, 00, 0, 0))
    pre_end_date = timezone.make_aware(datetime.datetime(2025, 5, 29, 23, 0, 0))

    training_start_date = timezone.make_aware(datetime.datetime(2025, 5, 30, 00, 0, 0))
    training_end_date = timezone.make_aware(datetime.datetime(2025, 5, 31, 00, 0, 0))
    
    post_start_date = timezone.make_aware(datetime.datetime(2025, 6, 1, 10, 0, 0))
    post_end_date = timezone.make_aware(datetime.datetime(2025, 6, 2, 18, 0, 0))
    
    delay_start_date = timezone.make_aware(datetime.datetime(2025, 6, 3, 10, 0, 0))
    delay_end_date = timezone.make_aware(datetime.datetime(2025, 5, 6, 4, 0, 0))

    current_time = timezone.now()

    if pre_start_date <= current_time <= pre_end_date:
        return 0
    elif training_start_date <= current_time <= training_end_date:
        return 1
    elif post_start_date <= current_time <= post_end_date:
        return 2
    elif delay_start_date <= current_time <= delay_end_date:
        return 3
    else:
        return -1

@csrf_exempt
def record(request, t):

    session_id = request.session.get('session_id')
    if session_id:
        session = Session.objects.get(id = session_id)
    else:
        login_form = LogInStudent()
        return render(request, 'login/login.html', {'login_form': login_form, 'error': 'サインインしてください。'})

    if request.method == 'POST' and request.FILES.get('audio'):

        reference_audio = Audio.objects.get(id=request.POST.get('reference_audio'))
        recorded_audio = request.FILES.get('audio')
        ativity_type = request.POST.get('activity_type')

        recording = Recording(
            original_audio = reference_audio
        )
        filename = f"{session.id}_{reference_audio.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
        recording.recorded_audio.save(filename, recorded_audio)
        recording.save()

        Activity.objects.create(
            session=session,
            recording=recording,
            type=ativity_type,
            time=timezone.now()
        )

        return JsonResponse({
            'status': 'success',
            'recording': {
                'id': recording.id,
                'url': recording.recorded_audio.url
            }
        })

    else:

        current_period = checkPeriod()

        if t == 0 and t == current_period:
            return HttpResponse("Pre-training")
        elif t == 2 and t == current_period:
            return HttpResponse("Post-training")
        elif t == 3 and t == current_period:
            return HttpResponse("Delayed recording")
        else:
            message = '現在は実験期間外のため、ログインできません。実験期間中に再度アクセスしてください。'
            redirect_url = f"{reverse('login:logout')}?{urlencode({'error': message})}"
            return redirect(redirect_url)
        
        
        # test_set = list(Audio.objects.all().filter(type = "test_nat"))
        # shuffle(test_set)
        # return render(request, 'record/record.html', {'test_set': test_set, 'MEDIA_URL': settings.MEDIA_URL})

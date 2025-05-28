from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.files import File
from django.shortcuts import render
from django.conf import settings
from django.utils import timezone
from pathlib import Path
from .models import Recording
from login.models import Session
from practice.models import Audio, Activity
from django.http import HttpResponse
from random import shuffle
import datetime

@csrf_exempt
def record(request):

    session = Session.objects.get(id = request.session['session_id'])
    # student_id = request.session.get('student_id')

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

        test_id = request.GET.get('t')
        
        pre_start_date = timezone.make_aware(datetime.datetime(2025, 5, 27, 00, 0, 0))
        pre_end_date = timezone.make_aware(datetime.datetime(2025, 5, 29, 18, 0, 0))
        
        post_start_date = timezone.make_aware(datetime.datetime(2025, 5, 30, 10, 0, 0))
        post_end_date = timezone.make_aware(datetime.datetime(2025, 6, 1, 18, 0, 0))
        
        delay_start_date = timezone.make_aware(datetime.datetime(2025, 6, 2, 10, 0, 0))
        delay_end_date = timezone.make_aware(datetime.datetime(2025, 5, 6, 4, 0, 0))
        
        current_time = timezone.now()
        
        if test_id == '0':
            if pre_start_date <= current_time <= pre_end_date:
                return HttpResponse("Pre-training")
            else:
                return HttpResponse("Pre-training not available yet")
        elif test_id == '2':
            if post_start_date <= current_time <= post_end_date:
                return HttpResponse("Post-training")
            else:
                return HttpResponse("Post-training not available yet")
        elif test_id == '1':
            if delay_start_date <= current_time <= delay_end_date:
                return HttpResponse("Delayed recording")
            else:
                return HttpResponse("Delayed recording not available yet")
        # test_set = list(Audio.objects.all().filter(type = "test_nat"))
        # shuffle(test_set)
        # return render(request, 'record/record.html', {'test_set': test_set, 'MEDIA_URL': settings.MEDIA_URL})

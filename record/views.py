from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files import File
from django.shortcuts import render
from django.conf import settings
from django.utils import timezone
from pathlib import Path
from .models import Recording
from login.models import Session
from practice.models import Audio, Activity

import datetime

@csrf_exempt
def record(request):

    session = Session.objects.get(id = request.session['session_id'])
    # student_id = request.session.get('student_id')

    if request.method == 'POST' and request.FILES.get('audio'):

        reference_audio = Audio.objects.get(id=request.POST.get('reference_audio'))
        recorded_audio = request.FILES.get('audio')

        recording = Recording(
            original_audio = reference_audio
        )
        filename = f"{session.id}_{reference_audio.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
        recording.recorded_audio.save(filename, recorded_audio)
        recording.save()

        Activity.objects.create(
            session=session,
            recording=recording,
            type='test_pre_record',
            time=timezone.now()
        )

        # full_path = Path(settings.MEDIA_ROOT) / saved_path
        # with full_path.open(mode="rb") as f:
        #     original_audio =  reference_audio
        #     recording = Recording(
        #         original_audio = original_audio,
        #         recorded_audio = File(f, name=full_path.name))
        #     recording.save()

        return JsonResponse({'status': 'ok'})
    else:

        test_set = Audio.objects.all().filter(type = "test_nat")
        return render(request, 'record/record.html', {'test_set': test_set, 'MEDIA_URL': settings.MEDIA_URL})

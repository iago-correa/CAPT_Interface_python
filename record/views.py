from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.core.files import File
from django.shortcuts import render
from django.conf import settings
from pathlib import Path
from .models import Recording, Experiment
from login.models import Session
from practice.models import Audio

import datetime

@csrf_exempt
def record(request):

    session_id = request.session.get('session_id')
    student_id = request.session.get('student_id')

    if request.method == 'POST' and request.FILES.get('audio'):

        audio_file = request.FILES['audio']
        filename = f"recording/recording_{student_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
        saved_path = default_storage.save(filename, audio_file)

        full_path = Path(settings.MEDIA_ROOT) / saved_path
        with full_path.open(mode="rb") as f:
            original_audio =  Audio.objects.get(filename = 'test_audio.wav')
            recording = Recording(
                original_audio = original_audio,
                experiment = Experiment.objects.get(session = Session.objects.get(id = session_id)),
                recorded_audio = File(f, name=full_path.name))
            recording.save()

        return JsonResponse({'status': 'ok', 'path': saved_path})
    else:

        return render(request, 'record/record.html', {})

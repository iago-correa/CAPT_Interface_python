from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from urllib.parse import urlencode
from pydub import AudioSegment
from random import shuffle
import datetime
import io

from login.models import Session
from login.forms import LogInStudent
from practice.models import Audio, Activity
from .models import Recording
from login.utils import get_current_period

@csrf_exempt
def record(request, t):
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

    activity_type_map = {
        0: 'test_pre_record',
        1: 'train_record',
        2: 'test_post_record',
        3: 'test_delay_record',
    }
    current_activity_type = activity_type_map.get(t)

    if not current_activity_type:
        # Invalid 't' value for this view, or 't' maps to training period
        message = ''
        query_params = urlencode({'error': message})
        return redirect(f"{reverse('login:logout')}?{query_params}")

    if request.method == 'POST' and request.FILES.get('audio'):
        reference_audio_id = request.POST.get('reference_audio')
        activity_type_from_post = request.POST.get('activity_type')
        
        if activity_type_from_post != current_activity_type:
            return JsonResponse({'status': 'error', 'message': 'Activity type mismatch.'}, status=400)
        
        try:
            reference_audio = Audio.objects.get(id=reference_audio_id)
        except Audio.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Reference audio not found.'}, status=404)

        if current_activity_type != 'train_record':
            already_recorded_by_student = Recording.objects.filter(
                activities__session__student=student,
                activities__type=current_activity_type,
                original_audio=reference_audio
            ).exists()
            if already_recorded_by_student:
                return JsonResponse({
                    'status': 'error',
                    'message': 'This audio has already been recorded by you for this test type.'
                }, status=409)

        uploaded_audio_file = request.FILES.get('audio')

        try:
            audio_data_buffer = io.BytesIO(uploaded_audio_file.read())
            sound = AudioSegment.from_file(audio_data_buffer)
            
            wav_buffer = io.BytesIO()
            sound.export(wav_buffer, format="wav")
            wav_buffer.seek(0) 

            wav_filename = f"{session.id}_{reference_audio.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
            wav_content_file = ContentFile(wav_buffer.read(), name=wav_filename)

            recording = Recording(original_audio=reference_audio)
            recording.recorded_audio.save(wav_content_file.name, wav_content_file, save=True)

            Activity.objects.create(
                session=session,
                recording=recording,
                type=current_activity_type,
                time=timezone.now()
            )

            return JsonResponse({
                'status': 'success',
                'recording': {
                    'id': recording.id,
                    'url': recording.recorded_audio.url
                }
            })
        except Exception as e:
            # Log the error for debugging (e.g., print(e) or use Django's logging)
            print(f"Audio processing error: {e}") # Basic error logging
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to process audio file. Ensure it is a valid audio format.'
            }, status=500)
    
    else: # GET request
        page_current_period_check = get_current_period()

        if t != page_current_period_check:
            # If 't' from URL doesn't match the actual current period for recording sessions
            message = ''
            query_params = urlencode({'error': message})
            return redirect(f"{reverse('login:logout')}?{query_params}")

        target_audio_set_type = "test_nat"
        all_required_audios = list(Audio.objects.filter(type=target_audio_set_type))
        all_required_audios = all_required_audios[:3]
        total_required_count = len(all_required_audios)

        if current_activity_type != 'train_record':
            if total_required_count > 0:
                num_recorded_by_student = 0
                for audio_item_check in all_required_audios:
                    if Recording.objects.filter(
                        activities__session__student=student,
                        activities__type=current_activity_type,
                        original_audio=audio_item_check
                    ).exists():
                        num_recorded_by_student += 1
                
                if num_recorded_by_student >= total_required_count:
                    completion_message = "この録音セッションは既に完了しています。"
                    query_params = urlencode({'message': completion_message})
                    return redirect(f"{reverse('login:logout')}?{query_params}")

        raw_test_set = all_required_audios 
        shuffle(raw_test_set)

        processed_test_set = []
        for audio_item in raw_test_set:
            # Check if recorded by this student for this activity type across any session
            is_recorded = Recording.objects.filter(
                activities__session__student=student,
                activities__type=current_activity_type,
                original_audio=audio_item
            ).exists()
            processed_test_set.append({'audio': audio_item, 'is_recorded': is_recorded})
        
        return render(request, 'record/record.html', {
            'test_set': processed_test_set,
            'MEDIA_URL': settings.MEDIA_URL,
            'current_t': t, 
            'csrf_token_value': request.META.get('CSRF_COOKIE') 
        })
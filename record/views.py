from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
# from django.conf import settings # Not directly used in this function after changes
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from storages.backends.s3boto3 import S3Boto3Storage
from urllib.parse import urlencode
from pydub import AudioSegment
from random import shuffle
import datetime
import io
import os # Still used for PID, but not for path joining for S3/DB
import logging

logger = logging.getLogger(__name__)

from login.models import Session
from practice.models import Audio, Activity
from .models import Recording
from login.utils import get_current_period, get_signed_url

@csrf_exempt
def record(request, t):
    pid_prefix = f"[PID:{os.getpid()}]"
    session_id = request.session.get('session_id')
    s3_storage = S3Boto3Storage()

    if not session_id:
        # ... (error handling for no session_id)
        error_message = 'サインインしてください。'
        query_params = urlencode({'error': error_message})
        return redirect(f"{reverse('login:login')}?{query_params}")

    try:
        session_obj = Session.objects.get(id=session_id)
        student = session_obj.student
    except Session.DoesNotExist:
        # ... (error handling for invalid session)
        request.session.flush()
        error_message = '無効なセッションです。再度サインインしてください。'
        query_params = urlencode({'error': error_message})
        return redirect(f"{reverse('login:login')}?{query_params}")

    activity_type_map = {0: 'test_pre_record', 1: 'train_record', 2: 'test_post_record', 3: 'test_delay_record'}
    current_activity_type = activity_type_map.get(t)

    if not current_activity_type:
        # ... (error handling for invalid activity type)
        message = '無効なアクティビティタイプです。'
        query_params = urlencode({'error': message})
        return redirect(f"{reverse('login:logout')}?{query_params}")

    if request.method == 'POST' and request.FILES.get('audio'):
        reference_audio_id = request.POST.get('reference_audio')
        activity_type_from_post = request.POST.get('activity_type')

        if activity_type_from_post != current_activity_type:
            logger.warning(f"{pid_prefix} Activity type mismatch. POST: {activity_type_from_post}, Expected: {current_activity_type}")
            return JsonResponse({'status': 'error', 'message': 'Activity type mismatch.'}, status=400)

        try:
            reference_audio = Audio.objects.get(id=reference_audio_id)
        except Audio.DoesNotExist:
            logger.warning(f"{pid_prefix} Reference audio ID {reference_audio_id} not found.")
            return JsonResponse({'status': 'error', 'message': 'Reference audio not found.'}, status=404)

        if current_activity_type != 'train_record':
            if Recording.objects.filter(activities__session__student=student, activities__type=current_activity_type, original_audio=reference_audio).exists():
                logger.info(f"{pid_prefix} Student {student.id} already recorded audio {reference_audio.id} for {current_activity_type}.")
                return JsonResponse({'status': 'error', 'message': 'This audio has already been recorded by you for this test type.'}, status=409)

        uploaded_audio_file = request.FILES.get('audio')
        original_filename_from_client = uploaded_audio_file.name
        name_parts = original_filename_from_client.split('.')
        file_extension_from_client = name_parts[-1].lower() if len(name_parts) > 1 else None
        logger.info(f"{pid_prefix} Received file: {original_filename_from_client}, client ext: {file_extension_from_client}, content_type: {uploaded_audio_file.content_type}")

        audio_data_buffer = io.BytesIO(uploaded_audio_file.read())
        sound = None
        tried_formats = []

        try:
            # --- Audio Pydub Loading Attempts (same as before) ---
            sensible_extensions = ['wav', 'webm', 'ogg', 'mp4', 'm4a', 'aac']
            if file_extension_from_client and file_extension_from_client in sensible_extensions:
                logger.info(f"{pid_prefix} Attempt 1: Pydub load with client ext: '{file_extension_from_client}'")
                tried_formats.append(file_extension_from_client)
                try: sound = AudioSegment.from_file(audio_data_buffer, format=file_extension_from_client)
                except Exception as e: logger.warning(f"{pid_prefix} Pydub failed (client ext '{file_extension_from_client}'): {e}"); audio_data_buffer.seek(0); sound = None
            
            ios_formats_to_try = ['m4a', 'mp4', 'aac']
            if not sound:
                for fmt_ios in ios_formats_to_try:
                    if fmt_ios not in tried_formats:
                        logger.info(f"{pid_prefix} Attempt 2: Pydub load with iOS format: '{fmt_ios}'")
                        tried_formats.append(fmt_ios)
                        try: sound = AudioSegment.from_file(audio_data_buffer, format=fmt_ios);
                        except Exception as e: logger.warning(f"{pid_prefix} Pydub failed (iOS format '{fmt_ios}'): {e}"); audio_data_buffer.seek(0); sound = None
                    if sound: break
            
            if not sound:
                logger.info(f"{pid_prefix} Attempt 3: Pydub load with auto-detection.")
                tried_formats.append('auto-detect')
                try: sound = AudioSegment.from_file(audio_data_buffer)
                except Exception as e: logger.warning(f"{pid_prefix} Pydub auto-detection failed: {e}"); audio_data_buffer.seek(0); sound = None

            if not sound and 'wav' not in tried_formats:
                logger.info(f"{pid_prefix} Attempt 4: Pydub load as WAV fallback.")
                tried_formats.append('wav')
                try: sound = AudioSegment.from_file(audio_data_buffer, format="wav")
                except Exception as e: logger.warning(f"{pid_prefix} Pydub WAV fallback failed: {e}"); sound = None
            # --- End Pydub Loading ---

            if not sound:
                error_message_detail = f'Failed to process audio file. Tried: {", ".join(set(tried_formats))}.'
                logger.error(f"{pid_prefix} {error_message_detail} - All pydub loading attempts failed for {original_filename_from_client}.")
                return JsonResponse({'status': 'error', 'message': error_message_detail}, status=500)

            logger.info(f"{pid_prefix} Audio loaded successfully. Original format likely compatible with one of: {', '.join(set(tried_formats))}")
            
            wav_buffer = io.BytesIO()
            sound.export(wav_buffer, format="wav")
            wav_buffer.seek(0)

            wav_filename_base = f"{session_obj.id}_{reference_audio.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.wav"
            wav_content_file = ContentFile(wav_buffer.read(), name=wav_filename_base)

            # --- CORRECTED Path Handling with FORWARD SLASHES ---
            # 1. Define the path to be stored in the Database model's FileField.
            #    Uses forward slashes explicitly.
            db_model_path = f"recording/{str(student.id)}/{wav_filename_base}"
            logger.info(f"{pid_prefix} Path to be stored in DB FileField: '{db_model_path}'")

            # 2. Define the full S3 object key.
            #    Uses forward slashes explicitly.
            s3_full_object_key = f"media/{db_model_path}"
            logger.info(f"{pid_prefix} Full S3 object key for S3 operations: '{s3_full_object_key}'")
            
            # 3. Save to S3 using the full S3 object key.
            actual_key_on_s3 = s3_storage.save(s3_full_object_key, wav_content_file)
            logger.info(f"{pid_prefix} Actual key returned by s3_storage.save(): '{actual_key_on_s3}'")

            if not actual_key_on_s3:
                error_message_s3_save = "S3 storage failed to save the file or returned an empty key."
                logger.error(f"{pid_prefix} {error_message_s3_save} (intended key: {s3_full_object_key})")
                return JsonResponse({'status': 'error', 'message': error_message_s3_save}, status=500)
            
            key_for_signing_new_url = actual_key_on_s3
            # --- End CORRECTED Path Handling ---

            recording_instance = Recording(original_audio=reference_audio)
            recording_instance.recorded_audio.name = db_model_path # Store the path WITH FORWARD SLASHES and WITHOUT 'media/'
            recording_instance.save()
            logger.info(f"{pid_prefix} Recording instance saved. ID: {recording_instance.id}, DB audio_path: '{recording_instance.recorded_audio.name}'")

            logger.info(f"{pid_prefix} Attempting to get signed URL for S3 key: '{key_for_signing_new_url}'")
            recording_signed_url = get_signed_url(key_for_signing_new_url) # This key should be the full S3 key like "media/recording/..."
            logger.info(f"{pid_prefix} Signed URL for new recording: '{recording_signed_url}'")

            if not recording_signed_url:
                error_msg_signed_url = f"get_signed_url returned None/empty for new S3 key: {key_for_signing_new_url}."
                logger.error(f"{pid_prefix} {error_msg_signed_url}")
                return JsonResponse({
                    'status': 'success', 
                    'recording': { 'id': recording_instance.id, 'url': None }
                })

            Activity.objects.create(
                session=session_obj,
                recording=recording_instance,
                type=current_activity_type,
                time=timezone.now()
            )
            logger.info(f"{pid_prefix} Activity created for recording ID: {recording_instance.id}")

            return JsonResponse({
                'status': 'success',
                'recording': {
                    'id': recording_instance.id,
                    'url': recording_signed_url
                }
            })
        except Exception as e:
            logger.exception(f"{pid_prefix} Overall error in POST /record/{t}/ for student {student.id}, audio {reference_audio_id if 'reference_audio_id' in locals() else 'unknown'}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)

    else: # GET request
        # ... (Your existing GET request logic remains here, ensure it's correct for 'record.html') ...
        logger.debug(f"{pid_prefix} GET request for /record/{t}/ by student {student.id if 'student' in locals() else 'unknown'}")
        # ... (rest of your GET logic)
        # Ensure settings.MEDIA_URL is correctly configured if used directly in templates.
        # For S3, signed URLs are generally preferred over direct MEDIA_URL access.
        page_current_period_check = get_current_period()

        if t != page_current_period_check:
            message = '' 
            query_params = urlencode({'error': message})
            logger.info(f"{pid_prefix} Mismatch t ({t}) and current_period ({page_current_period_check}). Redirecting to logout.")
            return redirect(f"{reverse('login:logout')}?{query_params}")

        target_audio_set_type = "test_nat" 
        all_required_audios = list(Audio.objects.filter(type=target_audio_set_type))
        total_required_count = len(all_required_audios)

        if current_activity_type != 'train_record':
            if total_required_count > 0:
                num_recorded_by_student = Recording.objects.filter(
                    activities__session__student=student, 
                    activities__type=current_activity_type, 
                    original_audio__in=all_required_audios
                ).distinct().count() # More efficient count
                
                if num_recorded_by_student >= total_required_count:
                    completion_message = "この録音セッションは既に完了しています。"
                    query_params = urlencode({'message': completion_message})
                    logger.info(f"{pid_prefix} Recording session already completed for student {student.id}, type {current_activity_type}. Redirecting.")
                    return redirect(f"{reverse('login:logout')}?{query_params}")

        raw_test_set = all_required_audios 
        shuffle(raw_test_set)
        processed_test_set = []
        for audio_item in raw_test_set:
            is_recorded = Recording.objects.filter(activities__session__student=student, activities__type=current_activity_type, original_audio=audio_item).exists()
            processed_test_set.append({'audio': audio_item, 'is_recorded': is_recorded})
        
        return render(request, 'record/record.html', {
            'test_set': processed_test_set,
            # 'MEDIA_URL': settings.MEDIA_URL, # MEDIA_URL might not be needed if using signed URLs for everything
            'current_t': t, 
            'csrf_token_value': request.META.get('CSRF_COOKIE') 
        })
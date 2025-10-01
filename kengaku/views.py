from django.shortcuts import render
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import JsonResponse
from pydub import AudioSegment
from .cosyvoice_service import init_cosy
from cosyvoice.utils.file_utils import load_wav
import os
import io
import logging
import torchaudio

logger = logging.getLogger(__name__)

SENTENCES_LIST = [
    ['sentence01', 'Learning English every day helps me speak clearly and understand others well.'],
    ['sentence02', 'Many people think of technology as a modern concept.'],
    ['sentence03', 'This tool can help us to predict the weather design earthquake proof buildings or analyze DNA.'],
    ['sentence04', 'Humanity had finally entered the era of mobile computing in which the internet literally sits in our hands.']   
]

def path_from_id(user_id, wav_id):
    
    wav_path = os.path.join('audio', user_id, wav_id+'.wav')
    wav_path = os.path.normpath(wav_path).replace('\\', '/')
    
    return wav_path


def generate_golden_speaker(recording_path, gs_dir):

    waveform, sr = torchaudio.load(recording_path)
    if sr != 16000:
        resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=16000)
        waveform = resampler(waveform)
        torchaudio.save(recording_path, waveform, 16000)

    os.makedirs(gs_dir, exist_ok=True)

    cosyvoice_model = init_cosy()           
    prompt = load_wav(recording_path, 16000)  # same prompt for all synths
    
    for fname, text in SENTENCES_LIST:
        out_wav = os.path.join(gs_dir, f"{fname}.wav")
        
        for audio in cosyvoice_model.inference_cross_lingual(
                tts_text=text, 
                prompt_speech_16k=prompt,
                stream=False):
            torchaudio.save(out_wav, audio['tts_speech'], cosyvoice_model.sample_rate)


@csrf_exempt
def demo(request):

    if request.method == 'POST' and request.FILES.get('audio'):
            
        pid_prefix = f"[PID:{os.getpid()}]"

        reference_audio_id = request.POST.get('reference_audio')
        user_id = request.POST.get('user_id')
        initial_rec = request.POST.get('initial_rec').lower() == "true"

        uploaded_audio_file = request.FILES.get('audio')
        original_filename_from_client = uploaded_audio_file.name
        name_parts = original_filename_from_client.split('.')
        file_extension_from_client = name_parts[-1].lower() if len(name_parts) > 1 else None

        audio_data_buffer = io.BytesIO(uploaded_audio_file.read())
        sound = None
        tried_formats = []

        try:
            # --- Audio Pydub Loading Attempts ---
            sensible_extensions = ['wav', 'webm', 'ogg', 'mp4', 'm4a', 'aac']
            if file_extension_from_client in sensible_extensions:
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

            recording_id = f"{reference_audio_id}_recording"
            wav_filename_base = f"{recording_id}.wav"
            wav_content_file = ContentFile(wav_buffer.read(), name=wav_filename_base)

            save_file_path = f"recording/{str(user_id)}/{wav_filename_base}"
            logger.info(f"{pid_prefix} Path to be stored: '{save_file_path}'")

            if default_storage.exists(save_file_path):
                default_storage.delete(save_file_path)

            actual_path = default_storage.save(save_file_path, wav_content_file)
            logger.info(f"{pid_prefix} File successfully saved to: '{actual_path}'")
        
            if initial_rec:
                
                recording_path = os.path.join(settings.MEDIA_ROOT, actual_path)
                gs_dir = f"{settings.MEDIA_ROOT}/gs/{str(user_id)}"
                generate_golden_speaker(recording_path, gs_dir)
            
            return JsonResponse({
                'status': 'success',
                'recording': {
                    'id': recording_id,
                    'url': actual_path
                }
            })
        
        except Exception as e:
            logger.exception(f"{pid_prefix} Overall error in POST /demo/ for user {user_id}, audio {reference_audio_id if 'reference_audio_id' in locals() else 'unknown'}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    
        
    else: # GET request
        
        user_id = '01'
        
        user_data_path  = os.path.join('media', 'recording', user_id)
        # Files not generated yet, need initial recording
        initial_rec = not os.path.isdir(user_data_path)
        
        context = {'csrf_token_value': request.META.get('CSRF_COOKIE'),
                   'user_id': user_id,
                   'initial_rec': initial_rec,
                   'audio_data': SENTENCES_LIST}
        
        return render(request, 'kengaku/demo.html', context)
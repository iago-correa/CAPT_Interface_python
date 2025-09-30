import os
import sys
from django.conf import settings
from pathlib import Path

COSY_ROOT = settings.COSY_ROOT
MODEL_DIR = settings.COSY_MODEL_DIR

if not COSY_ROOT or not MODEL_DIR:
    raise RuntimeError("Please set COSY_ROOT and COSY_MODEL_DIR in your environment.")

if COSY_ROOT not in sys.path:
    sys.path.append(COSY_ROOT)
    
matcha_path = os.path.join(COSY_ROOT, "third_party", "Matcha-TTS")
if matcha_path not in sys.path:
    sys.path.insert(0, matcha_path)

# Imports from cozy repo
from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav
import torchaudio

# Load model ONCE (module import time)
cosyvoice_model = None
def init_cosy():
    global cosyvoice_model
    if cosyvoice_model is None:
        cosyvoice_model = CosyVoice2(MODEL_DIR, load_jit=False, load_trt=False, fp16=False)
    return cosyvoice_model

def synthesize_zero_shot(prompt_wav_path, text, out_wav_path):

    cosyvoice_model = init_cosy()
    prompt = load_wav(prompt_wav_path, 16000)
    for i, j in enumerate(cosyvoice_model.inference_zero_shot(text, "", prompt, stream=False)):
        torchaudio.save(out_wav_path, j['tts_speech'], cosyvoice_model.sample_rate)

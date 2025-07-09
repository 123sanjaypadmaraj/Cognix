import whisper
import os

def transcribe_audio(audio_path, model_name="base"):
    if not os.path.exists(audio_path):
        print("[❌ Audio path missing]")
        return ""
    try:
        model = whisper.load_model(model_name)
        result = model.transcribe(audio_path)
        return result['text']
    except Exception as e:
        print(f"[❌ Whisper Error]: {e}")
        return ""

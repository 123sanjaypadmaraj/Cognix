import sounddevice as sd
import soundfile as sf

def record_audio(filename="voice.wav", duration=5, samplerate=44100):
    print("[🎙️ Recording Audio...]")
    try:
        audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1)
        sd.wait()
        sf.write(filename, audio, samplerate)
        return filename
    except Exception as e:
        print(f"[❌ Audio Error]: {e}")
        return None

# =====================================
# utils/speech_input.py – Voice to Text Handler
# =====================================

import speech_recognition as sr

def listen_and_transcribe():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("[🎙️ Listening... Speak now]")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        print(f"[🗣️ You said]: {text}")
        return text
    except sr.UnknownValueError:
        print("[❌ Could not understand audio]")
    except sr.RequestError as e:
        print(f"[⚠️ API Error]: {e}")

    return None

# === Test ===
if __name__ == "__main__":
    print(listen_and_transcribe())
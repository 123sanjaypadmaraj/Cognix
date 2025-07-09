import pyttsx3

def speak(text, rate=170):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', rate)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"[❌ TTS Error]: {e}")

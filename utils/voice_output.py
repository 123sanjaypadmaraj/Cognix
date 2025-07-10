# =====================================
# utils/voice_output.py – TTS Helper
# =====================================

import pyttsx3

class VoiceOutput:
    def __init__(self, rate=170, volume=1.0, voice_index=0):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', rate)
        self.engine.setProperty('volume', volume)

        voices = self.engine.getProperty('voices')
        if voices:
            self.engine.setProperty('voice', voices[voice_index % len(voices)].id)

    def say(self, text):
        print(f"[🗣️ Speaking]: {text}")
        self.engine.say(text)
        self.engine.runAndWait()

# === Test ===
if __name__ == "__main__":
    speaker = VoiceOutput()
    speaker.say("Hello, I am your Cognix assistant.")

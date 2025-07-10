# utils/wakeword.py
import queue
import sounddevice as sd
import vosk
import json

MODEL_PATH = "vosk-model-small-en-us-0.15"
WAKE_WORD = "hey cognix"

q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status)
    q.put(bytes(indata))

def listen_for_wakeword():
    print("[🎧 Waiting for wake word: 'Hey Cognix']")
    model = vosk.Model(MODEL_PATH)
    recognizer = vosk.KaldiRecognizer(model, 16000)

    with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                           channels=1, callback=callback):
        while True:
            data = q.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "")
                print(f"[👂 Heard]: {text}")
                if WAKE_WORD in text.lower():
                    print("[✅ Wake word detected]")
                    return True

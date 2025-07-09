import time
from core.memory import PerceptDB
from core.graph import MemoryGraph
from core.search import PerceptSearch
from interface.tts import speak
from audio.mic import record_audio
from audio.transcribe import transcribe_audio
from core.percept import Percept
from core.safety import detect_safety_risk
from llm.planner import suggest_next_action
from agent.scheduler import remind_upcoming_tasks

db = PerceptDB()
search = PerceptSearch()
search.preload(db)
graph = MemoryGraph()

def create_percept():
    audio_path = record_audio()
    text = transcribe_audio(audio_path)
    if not text.strip(): return
    tags = ["voice"]
    emotion = "neutral"
    if detect_safety_risk(text, "audio"):
        tags.append("sensitive")
        emotion = "alert"
    p = Percept(text=text, audio_path=audio_path, tags=tags, emotion=emotion)
    db.insert(p)
    search.index(text)
    graph.add(p)
    print(f"[🧠 Memory Captured]: {text}")

def passive_loop():
    while True:
        create_percept()
        remind_upcoming_tasks()
        memory_text = "\n".join([t for _, t in db.get_all_percepts()[-10:]])
        action = suggest_next_action(memory_text)
        print(f"[🤖 Suggestion]: {action}")
        speak(action)
        time.sleep(300)  # every 5 mins

if __name__ == "__main__":
    passive_loop()

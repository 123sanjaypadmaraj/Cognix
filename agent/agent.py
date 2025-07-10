# =====================================
# agent/agent.py – Passive Voice Agent
# =====================================

from core.intent_parser import detect_intent
from core.memory import PerceptDB
from core.search import PerceptSearch
from core.percept import Percept
from core.summarizer import summarize_day
from llm.fallback_llm import query_fallback_llm
from utils.speech_input import listen_and_transcribe
from utils.context import get_context
import pyttsx3
import time

# Temporary fallback for missing breakdown_goal
try:
    from llm.planner import breakdown_goal
except ImportError:
    def breakdown_goal(goal):
        print(f"[⚠️ Fallback]: No breakdown module. Simulating for goal: {goal}")
        return [f"Step 1 of {goal}", f"Step 2 of {goal}"]


def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 170)
    engine.say(text)
    engine.runAndWait()


def handle_passive_input(user_input: str, db, search):
    intent_data = detect_intent(user_input)

    # Ensure correct structure
    if not isinstance(intent_data, dict):
        speak(query_fallback_llm(user_input))
        return

    intent = intent_data.get("intent")
    params = intent_data.get("parameters", {})

    if intent == "reminder":
        task = params.get("task", "")
        time_str = params.get("time", "soon")
        with open("reminders.txt", "a") as f:
            f.write(f"⏰ Reminder: {task} at {time_str}\n")
        speak(f"Okay, I'll remind you to {task} at {time_str}.")

    elif intent == "note":
        content = params.get("content", "")
        if content:
            p = Percept(text=content, tags=["note"])
            db.insert(p)
            speak("Got it. Note saved.")

    elif intent == "journal":
        content = params.get("content", "")
        if content:
            p = Percept(text=content, tags=["journal"])
            db.insert(p)
            speak("Journal entry added.")

    elif intent == "recall":
        query = params.get("query", "")
        if query:
            results = search.search(query)
            if results:
                speak("Here's what I found:")
                for _, text in results:
                    speak(text)
            else:
                speak("I couldn't find anything related.")

    elif intent == "summary":
        speak("Here's your daily summary:")
        summarize_day()

    elif intent == "goal_breakdown":
        goal = params.get("goal", "")
        if goal:
            breakdown_goal(goal)

    elif intent == "plan_day":
        goal = params.get("goal", "your schedule")
        speak(f"Planning your day around {goal}.")

    else:
        speak(query_fallback_llm(user_input))


if __name__ == "__main__":
    db = PerceptDB()
    search = PerceptSearch()
    search.preload(db)

    print("[🤖 Cognix+ Passive Agent Started – Listening continuously]")
    speak("Cognix agent activated and listening.")

    while True:
        try:
            user_input = listen_and_transcribe()
            if user_input:
                context = get_context()
                print(f"[⏱️ Context]: {context['time_of_day']} on {context['day']}, recent: {', '.join(context['recent_keywords'])}")
                handle_passive_input(user_input, db, search)
        except Exception as e:
            print(f"[⚠️ Error]: {e}")
        time.sleep(2)

# =====================================
# main.py – Unified Launcher for Cognix+ (Autonomous + Multi-mode)
# =====================================

import argparse
import os
import time
from core.intent_parser import detect_intent
from core.memory import PerceptDB
from core.search import PerceptSearch
from core.percept import Percept
from core.summarizer import summarize_day
from core.emotion import detect_emotion
from core.personalization import suggest_break_or_focus
from llm.planner import breakdown_goal
from llm.fallback_llm import query_fallback_llm
from utils.speech_input import listen_and_transcribe
from utils.context import get_context
from utils.voice_output import VoiceOutput
from utils.wakeword import listen_for_wakeword


def handle_autonomous_input(user_input, db, search, speaker):
    intent_data = detect_intent(user_input)
    intent = intent_data.get("intent")
    params = intent_data.get("parameters", intent_data)
    emotion = detect_emotion(user_input)

    if intent == "reminder":
        task = params.get("task", "")
        time_str = params.get("time", "soon")
        with open("reminders.txt", "a") as f:
            f.write(f"⏰ Reminder: {task} at {time_str}\n")
        speaker.say(f"I'll remind you to {task} at {time_str}.")

    elif intent == "note":
        p = Percept(text=params["content"], tags=["note"], emotion=emotion)
        db.insert(p)
        speaker.say("Note saved.")

    elif intent == "journal":
        p = Percept(text=params["content"], tags=["journal"], emotion=emotion)
        db.insert(p)
        speaker.say("Journal entry added.")

    elif intent == "recall":
        results = search.search(params["query"])
        if results:
            speaker.say("Here's what I found:")
            for _, text in results:
                speaker.say(text)
        else:
            speaker.say("I couldn't find anything about that.")

    elif intent == "summary":
        speaker.say("Here’s your summary of the day:")
        summarize_day()

    elif intent == "goal_breakdown":
        breakdown_goal(params["goal"])

    elif intent == "plan_day":
        goal = params.get("goal", "your schedule")
        speaker.say(f"Planning your day around {goal}.")

    else:
        response = query_fallback_llm(user_input)
        speaker.say(response)


def get_greeting():
    from datetime import datetime
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning! How can I help you today?"
    elif hour < 18:
        return "Good afternoon! Ready to get things done?"
    else:
        return "Good evening! Hope you had a productive day."


def run_autonomous_agent():
    db = PerceptDB()
    search = PerceptSearch()
    search.preload(db)
    speaker = VoiceOutput()

    print("[🤖 Cognix+ Autonomous Agent Running...]")
    speaker.say(get_greeting())

    while True:
        listen_for_wakeword()
        suggestion = suggest_break_or_focus()
        if suggestion:
            speaker.say(suggestion)

        speaker.say("Yes? I'm listening.")
        user_input = listen_and_transcribe()
        if user_input:
            context = get_context()
            print(f"[⏱️ Context]: {context['time_of_day']} on {context['day']}, recent: {', '.join(context['recent_keywords'])}")
            handle_autonomous_input(user_input, db, search, speaker)
        time.sleep(2)


def run_cli():
    from interface.cli import smart_memory_query
    from core.memory import PerceptDB
    from core.search import PerceptSearch
    db = PerceptDB()
    search = PerceptSearch()
    search.preload(db)
    while True:
        query = input("🔎 Ask Cognix something ('exit' to quit): ")
        if query.lower() == "exit":
            break
        smart_memory_query(db, search, query)


def run_ui():
    os.system("python interface/web.py")


def run_agent_loop():
    os.system("python agent/main_loop.py")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="🧠 Cognix+ AI Twin Launcher")
    parser.add_argument("--mode", choices=["cli", "ui", "agent", "auto"], default="auto", help="Run mode: cli, ui, agent, or auto")
    args = parser.parse_args()

    if args.mode == "cli":
        run_cli()
    elif args.mode == "ui":
        run_ui()
    elif args.mode == "agent":
        run_agent_loop()
    elif args.mode == "auto":
        run_autonomous_agent()

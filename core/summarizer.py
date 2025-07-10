# =====================================
# core/summarizer.py – Daily Summary (with Voice Output)
# =====================================

from core.memory import PerceptDB
from utils.voice_output import VoiceOutput

speaker = VoiceOutput()

def summarize_day():
    db = PerceptDB()
    percepts = db.get_all_percepts()
    if not percepts:
        speaker.say("No memory captured today.")
        return

    summary = "Today, your memory captured:\n"
    for time, text in percepts[-10:]:
        hour = time.split("T")[-1][:5]
        line = f"[{hour}] {text[:80]}...\n"
        summary += line
        print(line.strip())

    print("\n[🗣️ Speaking Summary...]")
    speaker.say(summary)

# === Optional Test ===
if __name__ == "__main__":
    summarize_day()

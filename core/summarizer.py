# =====================================
# core/summarizer.py – Daily Summary (with Voice Output)
# =====================================

from core.memory import PerceptDB
from utils.voice_output import VoiceOutput
from core.personalization import analyze_user_trends

speaker = VoiceOutput()


emotions = [row[6] for row in db.get_all_percepts()]
counts = Counter(emotions)
dominant = counts.most_common(1)[0][0]
summary += f"\nEmotion trend: You mostly felt {dominant} today."

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
        summary += "\n\n" + analyze_user_trends()

    print("\n[🗣️ Speaking Summary...]")
    speaker.say(summary)

# === Optional Test ===
if __name__ == "__main__":
    summarize_day()

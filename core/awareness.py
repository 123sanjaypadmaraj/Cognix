from collections import Counter
import os
import pyttsx3

class AwarenessEngine:
    def __init__(self, db):
        self.db = db
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 170)

    def analyze_and_speak(self):
        texts = self.db.get_recent_texts()
        common = Counter(" ".join(texts).split()).most_common(5)
        keywords = [word for word, count in common if len(word) > 4]
        if keywords:
            msg = f"You often mentioned: {', '.join(keywords)}"
            print(f"[🧠 Awareness]: {msg}")
            self.engine.say(msg)
            self.engine.runAndWait()
            with open("reminders.txt", "a") as f:
                for word in keywords:
                    f.write(f"Remember to check on: {word}\n")

    def plan_goals(self):
        if not os.path.exists("reminders.txt"):
            return
        with open("reminders.txt", "r") as f:
            goals = [line.split("on: ")[-1] for line in f if "on:" in line]
        if goals:
            msg = f"Today's focus: {', '.join(set(goals))}"
            print(f"[📌 Goals]: {msg}")
            self.engine.say(msg)
            self.engine.runAndWait()

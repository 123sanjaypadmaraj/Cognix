# =====================================
# core/personalization.py – User Behavior Tracker
# =====================================

import datetime
from collections import Counter
from core.memory import PerceptDB


def analyze_user_trends():
    db = PerceptDB()
    recent = db.get_all_percepts()[-50:]
    if not recent:
        return "No usage trends yet."

    words = " ".join([text.lower() for _, text in recent]).split()
    freq = Counter(words)
    common = [word for word, count in freq.most_common(5) if len(word) > 4]

    return f"You've recently focused a lot on: {', '.join(common)}."


def suggest_break_or_focus():
    now = datetime.datetime.now()
    hour = now.hour
    if hour in [11, 14, 17]:
        return "It might be a good time to take a short break."
    elif hour in [9, 18]:
        return "Shall we plan your day or reflect on what’s next?"
    return None


# === Example ===
if __name__ == "__main__":
    print(analyze_user_trends())
    print(suggest_break_or_focus())

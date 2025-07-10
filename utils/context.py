# =====================================
# utils/context.py – Context Awareness Helper
# =====================================

import datetime
from core.memory import PerceptDB
from collections import Counter


def get_context():
    now = datetime.datetime.now()
    hour = now.hour
    day = now.strftime("%A")
    time_of_day = (
        "morning" if hour < 12 else
        "afternoon" if hour < 18 else
        "evening"
    )

    db = PerceptDB()
    recent_texts = [text for _, text in db.get_all_percepts()[-20:]]
    all_words = " ".join(recent_texts).lower().split()
    common_words = [word for word, count in Counter(all_words).most_common(5)]

    return {
        "day": day,
        "time_of_day": time_of_day,
        "recent_keywords": common_words
    }

# === Test ===
if __name__ == "__main__":
    print(get_context())

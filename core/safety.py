import datetime

SENSITIVE_KEYWORDS = ["help", "suicide", "abuse", "violence", "hurt", "kill", "emergency", "panic"]

def detect_safety_risk(text, source="audio"):
    found = [word for word in SENSITIVE_KEYWORDS if word in text.lower()]
    if found:
        with open("safety_log.txt", "a") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] {source.upper()} RISK: {text}\n")
        print(f"[⚠️ SAFETY WARNING]: {text}")
        return True
    return False

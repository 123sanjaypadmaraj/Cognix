# ============================================
# Cognix+ Intent Parser – Natural Language to Command
# Supports 50+ daily assistant phrases
# ============================================

import re
from llm.gemma_agent import query_llm

# === Simple intent patterns ===
INTENT_PATTERNS = [
    ("reminder", r"remind me to (?P<task>.+?)( at (?P<time>.+))?$"),
    ("note", r"(?:note|log): (?P<content>.+)"),
    ("journal", r"(?:journal|entry): (?P<content>.+)"),
    ("recall", r"(?:what did i say about|recall|search memory for) (?P<query>.+)"),
    ("summary", r"summarize (?:my|the) day"),
    ("plan_day", r"plan my day(?: around (?P<goal>.+))?"),
    ("goal_breakdown", r"break down (?P<goal>.+) into steps"),
    ("suggest_next", r"(what should i do next|suggest next step)"),
    ("tasks_today", r"show (?:my )?tasks(?: for today)?"),
    ("add_task", r"(?:add|create) (?:a )?task(?: to)? (?P<task>.+)"),
    ("cancel_reminder", r"cancel (?:the )?reminder(?: for)? (?P<task>.+)"),
    ("summarize_week", r"summarize (?:my )?week"),
    ("mood_log", r"i feel (?P<mood>.+)"),
    ("focus_mode", r"(focus mode|hide non-urgent tasks)"),
    ("task_delay", r"delay task (?P<task>.+) by (?P<duration>\d+) (day|days|hour|hours)"),
    ("list_goals", r"what are my (top )?(?:3 )?goals"),
    ("timeline", r"when did i mention (?P<topic>.+)"),
    ("highlights", r"what were the highlights (?:of|from) (?:today|this week)"),
    ("most_mentioned", r"who or what have i mentioned the most"),
]


def detect_intent(text):
    text = text.lower().strip()

    # Try matching basic patterns
    for intent, pattern in INTENT_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return {"intent": intent, **match.groupdict(default="").copy()}

    # === Fallback to LLM ===
    prompt = f"""
You are an assistant that extracts structured commands from user sentences.
Respond ONLY in JSON. 
Input: "{text}"
Output format: {{"intent": intent_name, "parameters": {{key: value}}}}
"""
    try:
        result = query_llm(prompt)
        return eval(result.strip()) if result.strip().startswith("{") else {"intent": "unknown"}
    except Exception as e:
        print(f"[❌ Intent Fallback Error]: {e}")
        return {"intent": "unknown"}


# === Sample test ===
if __name__ == "__main__":
    samples = [
        "Remind me to take medicine at 8 AM",
        "Note: Remember to read the AI paper",
        "Plan my day around finishing the report",
        "Break down writing thesis into steps",
        "Summarize my day",
        "What did I say about gym?",
        "I feel optimistic",
        "Add a task to organize files",
    ]

    for s in samples:
        intent = detect_intent(s)
        print(f"[🧠] {s} → {intent}")

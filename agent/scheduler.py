import datetime
from interface.tts import speak

def remind_upcoming_tasks():
    try:
        now = datetime.datetime.now().strftime("%H:%M")
        with open("task_schedule.txt", "r") as f:
            for line in f:
                if line.startswith("[") and now in line:
                    task = line.split("] ")[-1].strip()
                    print(f"[⏰ Reminder]: {task}")
                    speak(f"Reminder: {task}")
    except FileNotFoundError:
        pass

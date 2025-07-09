import datetime

def log_event(message, filename="cognix_log.txt"):
    with open(filename, "a") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {message}\n")

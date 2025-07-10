# =====================================
# interface/cli_debug.py – Debug + Voice CLI
# =====================================

from core.search import PerceptSearch
from core.memory import PerceptDB
from utils.speech_input import listen_and_transcribe
from utils.voice_output import VoiceOutput
from interface.cli import handle_user_input

speaker = VoiceOutput()
db = PerceptDB()
search = PerceptSearch()
search.preload(db)

print("[🧠 Cognix+ Debug CLI Ready – Speak to interact]")
speaker.say("Welcome to Cognix debug CLI mode.")

while True:
    text = listen_and_transcribe()
    if text:
        handle_user_input(text, db, search)


def smart_memory_query(db, search: PerceptSearch, query: str):
    print(f"\n🔍 {query}")
    results = search.search(query)
    for score, text in results:
        print(f"• {text} (score: {score:.2f})")
        speaker.say(text)

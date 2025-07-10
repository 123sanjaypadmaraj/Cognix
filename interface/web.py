# =====================================
# interface/web.py – Gradio UI for Cognix+
# =====================================

import gradio as gr
from core.memory import PerceptDB
from core.search import PerceptSearch
from core.intent_parser import detect_intent
from core.percept import Percept
from core.emotion import detect_emotion
from core.personalization import analyze_user_trends
from llm.fallback_llm import query_fallback_llm
from utils.voice_output import VoiceOutput

speaker = VoiceOutput()
db = PerceptDB()
search = PerceptSearch()
search.preload(db)


def handle_input(user_input):
    intent_data = detect_intent(user_input)
    intent = intent_data.get("intent")
    params = intent_data.get("parameters", intent_data)
    emotion = detect_emotion(user_input)

    response = ""

    if intent == "note":
        p = Percept(text=params["content"], tags=["note"], emotion=emotion)
        db.insert(p)
        response = "Note saved."

    elif intent == "journal":
        p = Percept(text=params["content"], tags=["journal"], emotion=emotion)
        db.insert(p)
        response = "Journal entry added."

    elif intent == "recall":
        results = search.search(params["query"])
        if results:
            response = "\n".join([f"• {text}" for _, text in results])
        else:
            response = "I couldn't find anything about that."

    else:
        response = query_fallback_llm(user_input)

    speaker.say(response)
    return response


def show_memory():
    all_percepts = db.get_all_percepts()
    return "\n".join([f"[{t}] {txt}" for t, txt in all_percepts[-10:]])


def show_trends():
    return analyze_user_trends()


def launch_ui():
    with gr.Blocks(title="Cognix+ AI Twin") as app:
        gr.Markdown("# 🧠 Cognix+ Web Interface")
        inp = gr.Textbox(label="Ask me anything")
        out = gr.Textbox(label="Response")

        with gr.Row():
            btn = gr.Button("Send")
            btn2 = gr.Button("Show Memory")
            btn3 = gr.Button("User Trends")

        mem_out = gr.Textbox(label="Memory Log")
        trends_out = gr.Textbox(label="Behavior Trends")

        btn.click(handle_input, inp, out)
        btn2.click(show_memory, None, mem_out)
        btn3.click(show_trends, None, trends_out)

    app.launch()


if __name__ == "__main__":
    launch_ui()

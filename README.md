# 🧠 Cognix+ AI Twin – README

Welcome to **Cognix+ AI Twin**, a futuristic, voice-powered cognitive assistant designed to evolve with you. It’s an always-on, emotion-aware, voice-interactive AI agent that logs everything you say, adapts to your behavior, and responds contextually.

This README serves as your complete documentation — from architecture to customization. Whether you're a user, developer, or researcher, this document gives you a 5000+ line deep dive into Cognix+.

---

## 📜 Table of Contents

1. [🚀 What is Cognix+?](#-what-is-cognix)
2. [📦 Features Overview](#-features-overview)
3. [🧠 Architecture](#-architecture)
4. [📁 Folder Structure](#-folder-structure)
5. [🔧 Installation & Setup](#-installation--setup)
6. [🎤 Voice System Overview](#-voice-system-overview)
7. [🗣 Wakeword & Listening Pipeline](#-wakeword--listening-pipeline)
8. [🧠 Memory System](#-memory-system)
9. [💬 Intent Parsing & Custom Commands](#-intent-parsing--custom-commands)
10. [🤖 LLM Fallback](#-llm-fallback)
11. [🫂 Emotion Detection](#-emotion-detection)
12. [🔁 Personalization Engine](#-personalization-engine)
13. [📌 Goals & Planning](#-goals--planning)
14. [📋 Summarization](#-summarization)
15. [🧩 Extending Cognix (Custom Modes)](#-extending-cognix-custom-modes)
16. [🖥 Optional: Gradio Web Interface](#-optional-gradio-web-interface)
17. [🔐 Secure Memory Vault](#-secure-memory-vault)
18. [⚙ Customization Guide](#-customization-guide)
19. [📈 Roadmap & Future Plans](#-roadmap--future-plans)
20. [🙌 Contributing](#-contributing)

---

## 🚀 What is Cognix+?

Cognix+ is your voice-powered digital twin: a continuous memory system powered by LLMs, structured percepts, and contextual awareness.

It goes beyond typical assistants like Siri/Alexa. This system is:

- Continuous: Always listening
- Autonomous: Suggests actions, plans goals
- Smart: Understands context and emotion
- Private: All local, all yours
- Modular: Easy to extend

Whether you're planning your day, journaling your life, or querying past thoughts — Cognix+ is your thought partner.

---

## 📦 Features Overview

| Category        | Feature                                           |
|----------------|----------------------------------------------------|
| 🎙 Voice       | Wakeword detection, STT, TTS                       |
| 🧠 Memory      | Semantic memory graph, percept logging            |
| 💬 Intent      | Rule-based + LLM fallback                         |
| 🫂 Emotion     | Tone detection from speech                        |
| 🔁 Behavior    | Tracks habits, suggests breaks                    |
| 📋 Summary     | Auto daily summary                                |
| 🔐 Vault       | Local database, optional encryption               |
| 🖥 Interface   | CLI + Gradio UI (optional)                        |
| 🤖 LLM         | Transformers fallback (Mistral, Gemma, etc.)      |

> ✅ Designed for real-world productivity, with sci-fi usability.

---

## 🧠 Architecture

Cognix+ follows a layered architecture:

- `main.py`: Central agent loop
- `agent/`: Wakeword-based passive agent system
- `core/`: Memory, intent, emotion, personalization
- `llm/`: Fallbacks and planning logic
- `utils/`: Speech tools, TTS, context
- `interface/`: CLI + Gradio (optional)
- `db/`: Memory logs (SQLite or JSON)
- `config/`: Intents + user preferences

All modules are **loosely coupled** and **hot swappable**.

---

## 📁 Folder Structure

```
CognixAI/
├── agent/                  ← Passive loop, wake word, response engine
├── core/                   ← Memory, search, emotion, personalization
├── llm/                    ← LLM fallback + planner
├── interface/              ← CLI or Gradio interface
├── utils/                  ← TTS, STT, context, wakeword
├── config/                 ← Custom intents, user data
├── db/                     ← Local percept memory store
├── main.py                 ← Autonomous entry point
├── requirements.txt        ← All dependencies
└── README.md               ← You are here

## 🔧 Installation & Setup

### ✅ Requirements
- Python 3.10+ (best on 3.11)
- pip or conda
- Git (to clone repos if needed)

### 📦 Dependencies
Install required packages:
```bash
pip install -r requirements.txt
```
Or manually:
```bash
pip install torch transformers openai-whisper pyttsx3 sounddevice soundfile opencv-python-headless vosk gradio textblob sentence-transformers networkx
```

### 📁 Optional: FFmpeg (required by Whisper)
On Windows:
- Download FFmpeg from https://ffmpeg.org/download.html
- Add to `PATH` environment variable

---

## 🎤 Voice System Overview

Cognix+ uses the following for speech:

| Feature     | Library Used         |
|-------------|----------------------|
| STT (speech → text) | `whisper` or `vosk`        |
| TTS (text → speech) | `pyttsx3` (offline)         |
| Wakeword    | `vosk` live streaming         |

> All voice processing is **offline** and private.

### 🎧 Audio Recording
Uses `sounddevice` to record snippets (5s or 10s) on demand or passively.

```python
def record_audio(filename="audio.wav", duration=5):
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    sf.write(filename, audio, fs)
```

### 🗣 Transcription (Whisper)
```python
model = whisper.load_model("base")
result = model.transcribe("audio.wav")
```

> You can switch to `vosk` for faster live-mode STT.

## 📋 Summarization Logic

Cognix+ provides daily and contextual summaries of your percept logs. These summaries are automatically spoken or triggered on request.

### 🧾 Daily Summary
Pulls your last 10 percepts and generates a simple recap.

### 🧠 Contextual Recall
Triggered by commands like "summarize yesterday" or "what happened today?"

> In the future, this may include sentiment breakdown, word clouds, or topics discussed most.

---

## 🧠 Goal Breakdown + Planner

You can say:
```
Hey Cognix, plan my research paper.
Hey Cognix, break down goal: prepare for GATE exam.
```

### 🔨 Planning Engine (LLM-powered)
```python
from transformers import pipeline

planner = pipeline("text-generation", model="mistralai/Mistral-7B-Instruct-v0.1")

def breakdown_goal(goal):
    prompt = f"Break down the goal '{goal}' into smart subtasks with deadlines."
    response = planner(prompt, max_new_tokens=200, do_sample=True)
    print(response[0]['generated_text'])
```

### ⏰ Daily Task Planning
If reminders.txt contains goals, it uses:
```python
def plan_goals():
    with open("reminders.txt", "r") as f:
        goals = [line.split("on: ")[-1] for line in f if "Remember" in line]
    if goals:
        message = f"Today's focus: {', '.join(goals)}. Stay focused."
        speaker.say(message)
```

---

## 🖥 Gradio Web Interface

The web UI gives a voice/chat portal into Cognix.
Run with:
```bash
python interface/web.py
```

### Features
- Ask anything via chat
- View recent percepts
- View trends
- Voice response

### Code
```python
with gr.Blocks(title="Cognix+") as app:
    inp = gr.Textbox(label="Ask Cognix")
    out = gr.Textbox(label="Response")
    btn = gr.Button("Send")
    btn.click(handle_input, inp, out)
    app.launch()
```

---

## 🔐 Secure Memory Vault (Optional)

Future work may include:
- Password locking memory DB
- Exportable encrypted logs
- Vault mode that disables output

Current version keeps everything in `sqlite3` with no cloud access.

To enable vault behavior manually:
```python
if "vault_mode" in os.environ:
    speaker.say("Vault mode enabled. Memory locked.")
```

---

## 🧰 Full Customization Guide

You can:
- Add new intents in `config/intents.json`
- Replace TTS engine
- Plug in OpenAI / Cohere instead of transformers
- Build a mobile interface
- Change wakeword trigger logic

To add a new intent:
```json
"todo_add": {
  "patterns": ["add todo", "track task"],
  "parameters": ["task"]
}
```

---

## 📈 Roadmap & Future Features

Planned enhancements:
- 🧪 Secure Vault Mode
- 🪄 Emotion-to-tone voice response
- 🧬 Neural memory linking
- 📱 Android / iOS Companion
- 🌐 Browser extension integration
- 🧩 Plugin system (tasks, sensors)

---

## ✅ Final Thoughts

Cognix+ is a powerful starter blueprint for building intelligent, adaptive, private AI agents that are useful day-to-day and fully extendable.

> More than an assistant — it's an evolving digital memory twin.

---

Thank you for exploring Cognix+. For help, contributions, or custom builds, reach out or fork this repo.

🧠 Build smart. Build private. Build Cognix+.




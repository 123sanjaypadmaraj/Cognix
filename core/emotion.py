# =====================================
# core/emotion.py – Simple Emotion Detection (text-based)
# =====================================

from textblob import TextBlob

def detect_emotion(text):
    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity

    if polarity > 0.5:
        return "happy"
    elif 0.1 < polarity <= 0.5:
        return "positive"
    elif -0.1 <= polarity <= 0.1:
        return "neutral"
    elif -0.5 <= polarity < -0.1:
        return "sad"
    else:
        return "angry"

# === Example ===
if __name__ == "__main__":
    samples = [
        "I am so excited for today!",
        "This is fine, just a normal day.",
        "I'm feeling kind of down.",
        "I hate how things are going!"
    ]

    for text in samples:
        print(f"{text} => {detect_emotion(text)}")

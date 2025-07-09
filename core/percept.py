import uuid
import datetime

class Percept:
    def __init__(self, text, audio_path=None, image_path=None, tags=None, emotion=None, tone=None):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.datetime.now().isoformat()
        self.text = text
        self.audio_path = audio_path
        self.image_path = image_path
        self.tags = tags or []
        self.emotion = emotion
        self.tone = tone

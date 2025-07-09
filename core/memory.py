import sqlite3
from core.percept import Percept

class PerceptDB:
    def __init__(self, db_path="percepts.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS percepts (
            id TEXT PRIMARY KEY,
            timestamp TEXT,
            text TEXT,
            audio_path TEXT,
            image_path TEXT,
            tags TEXT,
            emotion TEXT,
            tone TEXT
        )''')
        self.conn.commit()

    def insert(self, percept: Percept):
        self.conn.execute("INSERT INTO percepts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (percept.id, percept.timestamp, percept.text,
            percept.audio_path, percept.image_path,
            ','.join(percept.tags), percept.emotion, percept.tone))
        self.conn.commit()

    def get_all_percepts(self):
        cursor = self.conn.execute("SELECT timestamp, text FROM percepts ORDER BY timestamp")
        return cursor.fetchall()

    def get_recent_texts(self, limit=20):
        cursor = self.conn.execute("SELECT text FROM percepts ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [row[0] for row in cursor.fetchall()]

    def get_percepts_by_keyword(self, keyword):
        cursor = self.conn.execute("SELECT timestamp, text FROM percepts WHERE text LIKE ? ORDER BY timestamp", (f"%{keyword}%",))
        return cursor.fetchall()

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.percept import Percept
from core.memory import PerceptDB

def insert_mock_data():
    db = PerceptDB()
    samples = [
        Percept(text="Discussed AI project", tags=["project"], emotion="curious"),
        Percept(text="Went to the gym", tags=["health"], emotion="positive"),
        Percept(text="Talked about quantum computing", tags=["study"], emotion="focused")
    ]
    for p in samples:
        db.insert(p)
        print(f"[✅ Inserted]: {p.text}")

if __name__ == "__main__":
    insert_mock_data()

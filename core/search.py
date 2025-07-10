import torch
from sentence_transformers import SentenceTransformer, util

class PerceptSearch:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embeddings = []
        self.texts = []

    def index(self, text):
        emb = self.model.encode(text, convert_to_tensor=True)
        self.texts.append(text)
        self.embeddings.append(emb)

    def search(self, query, top_k=3):
        if not self.embeddings:
            print("[❌ No embeddings available for semantic search]")
            return []
        q = self.model.encode(query, convert_to_tensor=True)
        # ✅ Fix: Stack all embeddings into a single tensor
        emb_tensor = torch.stack(self.embeddings)
        scores = util.cos_sim(q, emb_tensor)[0]
        top = sorted(zip(scores, self.texts), key=lambda x: x[0], reverse=True)[:top_k]
        return top

    def preload(self, db):
        for _, text in db.get_all_percepts():
            print(f"[📥 Indexing]: {text}")
            self.index(text)

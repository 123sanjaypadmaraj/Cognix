from sentence_transformers import SentenceTransformer, util

class PerceptSearch:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.embeddings = []
        self.texts = []

    def index(self, text):
        emb = self.model.encode(text, convert_to_tensor=True)
        self.embeddings.append(emb)
        self.texts.append(text)

    def search(self, query, top_k=3):
        if not self.embeddings:
            print("[❌ No percepts indexed for semantic search]")
            return []
        q = self.model.encode(query, convert_to_tensor=True)
        scores = util.cos_sim(q, self.embeddings)[0]
        top = sorted(zip(scores, self.texts), key=lambda x: x[0], reverse=True)[:top_k]
        return top

    def preload(self, db):
        for _, text in db.get_all_percepts():
            self.index(text)

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.memory import PerceptDB
from core.search import PerceptSearch

def run_search_test():
    db = PerceptDB()
    percepts = db.get_all_percepts()
    if not percepts:
        print("[❌ No percepts found in DB. Run `mock_data.py` first.]")
        return

    print("[📄 All Percepts in DB]")
    for t, text in percepts:
        print(f"[{t}] {text}")

    search = PerceptSearch()
    search.preload(db)

    print("\n🔍 Searching for 'AI project'")
    results = search.search("AI project")

    if not results:
        print("[❌ Search returned nothing — embeddings may be empty]")
    else:
        for score, text in results:
            print(f"• {text} (score: {score:.2f})")

if __name__ == "__main__":
    run_search_test()

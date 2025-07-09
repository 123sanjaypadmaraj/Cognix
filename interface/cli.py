from core.search import PerceptSearch
from core.memory import PerceptDB

def smart_memory_query(db, search: PerceptSearch, query: str):
    print(f"\n🔍 {query}")
    results = search.search(query)
    for score, text in results:
        print(f"• {text} (score: {score:.2f})")

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from core.memory import PerceptDB
from core.search import PerceptSearch

def run_search_test():
    db = PerceptDB()
    search = PerceptSearch()
    search.preload(db)
    results = search.search("AI project")
    for score, text in results:
        print(f"{score:.2f}: {text}")

if __name__ == "__main__":
    run_search_test()

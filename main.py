import argparse
import os

def run_cli():
    from interface.cli import smart_memory_query
    from core.memory import PerceptDB
    from core.search import PerceptSearch
    db = PerceptDB()
    search = PerceptSearch()
    search.preload(db)
    while True:
        query = input("🔎 Ask Cognix something ('exit' to quit): ")
        if query.lower() == "exit":
            break
        smart_memory_query(db, search, query)

def run_ui():
    os.system("python interface/gradio_ui.py")

def run_agent():
    os.system("python agent/main_loop.py")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="🧠 Cognix+ AI Twin Launcher")
    parser.add_argument("--mode", choices=["cli", "ui", "agent"], default="cli", help="Run mode: cli, ui, or agent")
    args = parser.parse_args()

    if args.mode == "cli":
        run_cli()
    elif args.mode == "ui":
        run_ui()
    elif args.mode == "agent":
        run_agent()

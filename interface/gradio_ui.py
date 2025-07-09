import gradio as gr
from llm.gemma_agent import query_llm
from llm.planner import summarize_day
from core.memory import PerceptDB

db = PerceptDB()

def chat_with_agent(prompt):
    memory = "\n".join([t for _, t in db.get_all_percepts()[-10:]])
    return query_llm(f"{prompt}\n\nMemory:\n{memory}")

def view_summary():
    memory = "\n".join([t for _, t in db.get_all_percepts()[-15:]])
    return summarize_day(memory)

demo = gr.Interface(
    fn=chat_with_agent,
    inputs="text",
    outputs="text",
    title="Cognix+ AI Twin",
    description="Ask anything. It remembers, reflects, and suggests.",
    live=True
)

dashboard = gr.TabbedInterface([demo, gr.Interface(view_summary, inputs=None, outputs="text")], ["Chat", "Summary"])

if __name__ == "__main__":
    dashboard.launch()

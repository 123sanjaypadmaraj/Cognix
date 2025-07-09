from llm.gemma_agent import query_llm

def generate_subtasks(goal):
    prompt = f"Break down this goal into 3 steps:\nGoal: {goal}\nSteps:"
    response = query_llm(prompt)
    return [line.strip("-• ") for line in response.split("\n") if line.strip()]

def suggest_next_action(memory_text):
    prompt = f"Based on this memory, what should I focus on next?\n{memory_text}\n\nSuggestion:"
    return query_llm(prompt)

def summarize_day(memory_text):
    prompt = f"You are my memory assistant. Summarize today's events:\n{memory_text}\n\nSummary:"
    return query_llm(prompt)

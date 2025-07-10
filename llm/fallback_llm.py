# =====================================
# llm/fallback_llm.py – LLM Query Fallback
# =====================================

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch

MODEL_NAME = "google/flan-t5-base"

print("[🤖 Loading fallback LLM...]")

# Load tokenizer and model (CPU-safe)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

def query_fallback_llm(prompt: str) -> str:
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True)
    outputs = model.generate(**inputs, max_new_tokens=100, do_sample=True, temperature=0.7)
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"[🧠 LLM Response]: {result}")
    return result

# === Example ===
if __name__ == "__main__":
    response = query_fallback_llm("Why is the sky blue?")
    print(response)

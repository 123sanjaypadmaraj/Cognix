# =====================================
# llm/fallback_llm.py – LLM Query Fallback
# =====================================

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# You can change this model to any small open LLM from HuggingFace
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.1"

print("[🤖 Loading fallback LLM...]")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float16, device_map="auto")


def query_fallback_llm(prompt):
    input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(model.device)
    output_ids = model.generate(input_ids, max_length=300, do_sample=True, top_k=50, temperature=0.7)
    output = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    print(f"[🧠 LLM Response]: {output}")
    return output


# === Example ===
if __name__ == "__main__":
    response = query_fallback_llm("Why is the sky blue?")
    print(response)

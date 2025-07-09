from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

print("[🤖 Loading Gemma LLM...]")
tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b-it")
model = AutoModelForCausalLM.from_pretrained("google/gemma-2b-it")
llm = pipeline("text-generation", model=model, tokenizer=tokenizer)

def query_llm(prompt, max_tokens=200):
    try:
        result = llm(prompt, max_new_tokens=max_tokens, do_sample=True, temperature=0.7)
        return result[0]['generated_text'][len(prompt):].strip()
    except Exception as e:
        print(f"[❌ LLM Error]: {e}")
        return "Sorry, I couldn't generate a response."

import pandas as pd
import requests
import re

def load_file():
    path = input("📂 Enter the path to your Excel or CSV file: ").strip().strip('"')
    try:
        if path.endswith(".xlsx"):
            df = pd.read_excel(path)
        elif path.endswith(".csv"):
            df = pd.read_csv(path)
        else:
            print("❌ Please use a .xlsx or .csv file.")
            exit()
        print(f"✅ File loaded successfully with {df.shape[0]} rows and {df.shape[1]} columns.")
        return df
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        exit()

def build_prompt(columns, question):
    return f"""
You're a helpful data assistant. A DataFrame called 'df' is already loaded with the following columns:
{', '.join(columns)}

The user wants to know: "{question}"

Write Python pandas code to answer this.
Only return clean code inside a Python code block.
Assign the result to a variable called 'result'. No extra explanations.
"""

def ask_llm(prompt):
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "mistral", "prompt": prompt, "stream": False}
        )
        return res.json()["response"]
    except Exception as e:
        print(f"❌ Error contacting Mistral via Ollama: {e}")
        exit()

def extract_code(response):
    match = re.search(r"```python(.*?)```", response, re.DOTALL)
    return match.group(1).strip() if match else response.strip()

def run_code(code, df):
    try:
        local_vars = {"df": df}
        exec(code, {}, local_vars)
        result = local_vars.get("result")
        if result is not None:
            print("\n✅ Here’s the result:\n")
            print(result)
        else:
            print("⚠️ Code ran, but no result was assigned.")
    except Exception as e:
        print(f"\n❌ Error running the code:\n{e}")

def main():
    print("🤖 Hello! I’m your local AI Data Assistant powered by Mistral.\n")
    df = load_file()

    while True:
        question = input("\n💬 What would you like to know about your data? (or type 'exit' to quit): ").strip()
        if question.lower() == "exit":
            print("👋 Okay, goodbye!")
            break

        prompt = build_prompt(df.columns, question)
        print("🧠 Thinking...")
        raw_response = ask_llm(prompt)
        code = extract_code(raw_response)

        print("\n📝 Generated Code:\n")
        print(code)
        run_code(code, df)

if __name__ == "__main__":
    main()

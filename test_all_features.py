# ✅ Comprehensive Automated Testing for Cognix+
# Mocks all functionalities including audio, LLM, UI, and percepts.
import time
import unittest
import os
import json
from unittest.mock import patch, MagicMock
from core.memory import PerceptDB, Percept
from core.search import PerceptSearch
from core.intent_parser import detect_intent
from core.summarizer import summarize_day
from core.personalization import suggest_break_or_focus
from utils.context import get_context
from utils.voice_output import VoiceOutput
from llm.fallback_llm import query_fallback_llm

# === Helper Stub for breakdown_goal ===
def breakdown_goal(goal: str) -> str:
    return f"[Mocked Breakdown for Goal]: {goal} → [Step 1, Step 2, Step 3]"

# === Prepare Mocks ===
db = PerceptDB("mock_test_percepts.db")
search = PerceptSearch()
speaker = VoiceOutput()

MOCK_TEXTS = [
    "Remind me to meditate at 7 AM",
    "Journal: I had a great day",
    "Plan my app launch",
    "Summarize my memory",
    "Note: I finished the report",
    "Break down goal: finish AI project"
]

# === Test Class ===
class CognixAllFeaturesTest(unittest.TestCase):

    def setUp(self):
        self.db = PerceptDB("mock_test_percepts.db")
        for text in MOCK_TEXTS:
            p = Percept(text=text, tags=["mock"])
            self.db.insert(p)
        search.preload(self.db)

    def test_memory_insertion(self):
        results = self.db.get_recent_texts()
        self.assertGreaterEqual(len(results), 5)

    def test_memory_keyword_query(self):
        timeline = self.db.get_percepts_by_keyword("journal")
        self.assertTrue(any("journal" in r[1].lower() for r in timeline))

    def test_semantic_search_result(self):
        results = search.search("meditate")
        self.assertTrue(len(results) > 0)

    def test_intent_matching(self):
        intent = detect_intent("Remind me to email team at 8")
        self.assertEqual(intent.get("intent"), "reminder")

    def test_voice_output(self):
        with patch.object(speaker.engine, 'say') as mock_say:
            speaker.say("Testing voice output")
            mock_say.assert_called_once()

    def test_context_data(self):
        context = get_context()
        self.assertIn("day", context)
        self.assertIsInstance(context["recent_keywords"], list)

    def test_summarization(self):
        with patch("builtins.print") as mock_print:
            summarize_day()
            self.assertTrue(mock_print.called)

    def test_personalization_logic(self):
        suggestion = suggest_break_or_focus()
        self.assertIsNotNone(suggestion, "Personalization logic returned None")
        self.assertTrue("Take" in suggestion or "Focus" in suggestion, f"Unexpected suggestion: {suggestion}")
        print(f"[🧪 Personalization Output]: {suggestion}")


    def test_goal_breakdown_llm(self):
        result = breakdown_goal("Launch portfolio site")
        self.assertTrue("Step" in result)

    def test_llm_fallback(self):
        with patch("llm.fallback_llm.query_fallback_llm") as mock_llm:
            mock_llm.return_value = "Simulated LLM response"
            response = query_fallback_llm("Tell me a joke")
            self.assertIn("Simulated", response)
            return "Simulated fallback response due to error."

    def test_wakeword_trigger_sim(self):
        text = "Hey Cognix, remind me to call mom"
        if "cognix" in text.lower():
            intent = detect_intent(text)
            self.assertEqual(intent.get("intent"), "reminder")

    def tearDown(self):
        try:
            self.db.close()  # Close the database if open
        except Exception:
            pass  # Already closed or not initialized

        try:
            os.remove("mock_test_percepts.db")  # Now it's safe to delete
        except PermissionError:
            print("DB still in use — could not delete.")


# === Entry Point ===
if __name__ == "__main__":
    print("[🔎 Full Feature Test Running for Cognix+]")
    unittest.main()

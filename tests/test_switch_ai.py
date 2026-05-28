import unittest

from src.backend import default_state
from src.switch_ai import build_switch_ai_recommendation, default_switch_ai_memory


class SwitchAITests(unittest.TestCase):
    def test_recommendation_selects_required_outfit_categories(self):
        state = default_state()

        recommendation = build_switch_ai_recommendation(
            state,
            {
                "occasion": "Smart casual dinner",
                "budget": 120,
                "replaceMode": "some",
                "paidAllowed": True,
            },
        )

        selected_categories = {
            item["category"]
            for item in state["wardrobe"]
            if item["name"] in recommendation["outfitItems"]
        }
        self.assertTrue({"top", "bottom", "shoes"}.issubset(selected_categories))
        self.assertGreaterEqual(recommendation["confidence"], 70)
        self.assertEqual(recommendation["model"], "SwitchAI v1.0 local stylist brain")

    def test_feedback_memory_changes_future_ranking(self):
        state = default_state()
        state["switchAi"] = default_switch_ai_memory()
        state["switchAi"]["preferences"]["colors"]["black"] = 4

        recommendation = build_switch_ai_recommendation(
            state,
            {
                "occasion": "Concert",
                "budget": 40,
                "replaceMode": "none",
                "paidAllowed": False,
            },
        )

        self.assertIn("Black Relaxed Tee", recommendation["outfitItems"])


if __name__ == "__main__":
    unittest.main()

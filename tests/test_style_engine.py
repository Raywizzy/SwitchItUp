import unittest

from src.style_engine import (
    StyleRequest,
    WardrobeItem,
    build_style_plan,
    sample_request,
    sample_stylists,
    sample_wardrobe,
    select_outfit,
)


class StyleEngineTests(unittest.TestCase):
    def test_sample_plan_selects_complete_outfit(self):
        plan = build_style_plan(sample_wardrobe(), sample_stylists(), sample_request())

        self.assertIn("White Oxford Shirt", plan.outfit_items)
        self.assertIn("Stone Chinos", plan.outfit_items)
        self.assertIn("White Trainers", plan.outfit_items)
        self.assertEqual(plan.missing_categories, ())
        self.assertGreaterEqual(plan.confidence_percent, 90)

    def test_missing_shoes_creates_replacement_suggestion(self):
        wardrobe = tuple(item for item in sample_wardrobe() if item.category != "shoes")
        plan = build_style_plan(wardrobe, sample_stylists(), sample_request())

        self.assertEqual(plan.missing_categories, ("shoes",))
        self.assertTrue(any("trainers" in suggestion for suggestion in plan.replacement_suggestions))

    def test_cold_weather_adds_jacket(self):
        outfit = select_outfit(
            sample_wardrobe(),
            StyleRequest("casual day out", 3, "cold", 40, False),
        )

        self.assertTrue(any(item.category == "jacket" for item in outfit))

    def test_invalid_category_is_rejected(self):
        wardrobe = (WardrobeItem("Mystery", "hat-but-not-valid", "red", 2, 1),)

        with self.assertRaisesRegex(ValueError, "invalid category"):
            select_outfit(wardrobe, sample_request())


if __name__ == "__main__":
    unittest.main()

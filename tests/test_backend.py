import tempfile
import unittest
from pathlib import Path

from src.backend import BackendError, JsonStore, SwitchItUpBackend


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.store_path = Path(self.tempdir.name) / "state.json"
        self.backend = SwitchItUpBackend(JsonStore(self.store_path))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_default_state_is_persisted(self):
        state = self.backend.get_state()

        self.assertEqual(state["profile"]["name"], "Raymond")
        self.assertEqual(len(state["wardrobe"]), 6)
        self.assertTrue(self.store_path.exists())

    def test_add_wardrobe_item_persists(self):
        result = self.backend.add_wardrobe_item(
            {
                "name": "Grey Knit Polo",
                "category": "top",
                "fit": "regular",
                "material": "cotton knit",
                "colorName": "grey",
                "formality": 3,
                "warmth": 1,
                "colors": ["#d1d5db", "#6b7280"],
            }
        )

        self.assertEqual(result["item"]["name"], "Grey Knit Polo")
        self.assertIn("Grey Knit Polo", [item["name"] for item in self.backend.get_state()["wardrobe"]])

    def test_uploaded_photo_is_saved_and_referenced(self):
        tiny_png = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
        )

        result = self.backend.add_wardrobe_item(
            {
                "name": "Uploaded Linen Shirt",
                "category": "top",
                "photoName": "linen-shirt.png",
                "photoData": tiny_png,
                "colors": ["#f8fafc", "#cbd5e1"],
            }
        )

        photo_path = result["item"]["photo"]
        self.assertTrue(photo_path.startswith("data/uploads/linen-shirt-"))
        self.assertTrue((self.store_path.parent / "uploads" / Path(photo_path).name).exists())

    def test_invalid_uploaded_photo_is_rejected(self):
        with self.assertRaisesRegex(BackendError, "valid base64"):
            self.backend.add_wardrobe_item(
                {
                    "name": "Broken Upload",
                    "category": "top",
                    "photoName": "broken.png",
                    "photoData": "data:image/png;base64,not-a-real-image",
                }
            )

    def test_invalid_wardrobe_category_is_rejected(self):
        with self.assertRaisesRegex(BackendError, "category is invalid"):
            self.backend.add_wardrobe_item({"name": "Mystery Hat", "category": "hat"})

    def test_style_request_returns_plan_and_persists_request(self):
        result = self.backend.create_style_request(
            {
                "occasion": "Smart casual dinner",
                "budget": 120,
                "replaceMode": "some",
                "delivery": "Within 24 hours",
                "paidAllowed": True,
            }
        )

        self.assertIn("Backend style plan selected", result["message"])
        self.assertGreaterEqual(result["confidence"], 90)
        self.assertEqual(len(self.backend.get_state()["styleRequests"]), 1)

    def test_wishlist_accept_adds_item_to_wardrobe(self):
        result = self.backend.wishlist_action("Structured navy blazer", "accept")
        wardrobe_names = [item["name"] for item in result["wardrobe"]]

        self.assertIn("Structured Navy Blazer", wardrobe_names)
        self.assertIn("accepted", result["message"])


if __name__ == "__main__":
    unittest.main()

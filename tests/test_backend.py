import tempfile
import unittest
from pathlib import Path

from src.backend import BackendError, JsonStore, SupabaseStateStore, SwitchItUpBackend


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

    def test_uploaded_photo_signature_must_match_type(self):
        fake_png = "data:image/png;base64,aGVsbG8="

        with self.assertRaisesRegex(BackendError, "does not match"):
            self.backend.add_wardrobe_item(
                {
                    "name": "Fake Upload",
                    "category": "top",
                    "photoName": "fake.png",
                    "photoData": fake_png,
                    "colors": ["#f8fafc", "#cbd5e1"],
                }
            )

    def test_invalid_wardrobe_category_is_rejected(self):
        with self.assertRaisesRegex(BackendError, "category is invalid"):
            self.backend.add_wardrobe_item({"name": "Mystery Hat", "category": "hat"})

    def test_measurements_are_validated_and_persisted(self):
        result = self.backend.update_measurements(
            {"heightCm": 181, "topSize": "L", "waistIn": 34, "shoeSize": "UK 11"}
        )

        self.assertEqual(result["profile"]["measurements"]["heightCm"], 181)
        self.assertEqual(self.backend.get_state()["profile"]["measurements"]["shoeSize"], "UK 11")

    def test_invalid_measurements_are_rejected(self):
        with self.assertRaisesRegex(BackendError, "heightCm must be between"):
            self.backend.update_measurements({"heightCm": 300})

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

    def test_invalid_style_request_mode_is_rejected(self):
        with self.assertRaisesRegex(BackendError, "replaceMode"):
            self.backend.create_style_request({"occasion": "Dinner", "replaceMode": "mystery"})

    def test_wishlist_accept_adds_item_to_wardrobe(self):
        result = self.backend.wishlist_action("Structured navy blazer", "accept")
        wardrobe_names = [item["name"] for item in result["wardrobe"]]

        self.assertIn("Structured Navy Blazer", wardrobe_names)
        self.assertIn("accepted", result["message"])

    def test_stylist_upgrade_creates_application_and_role(self):
        result = self.backend.upgrade_stylist_account(
            {"specialty": "AI-assisted smart casual styling", "plan": "pro_monthly"}
        )

        self.assertEqual(result["profile"]["role"], "stylist")
        self.assertEqual(result["application"]["status"], "active")
        self.assertEqual(len(self.backend.get_state()["stylistApplications"]), 1)

    def test_stylist_upgrade_is_idempotent_for_active_account(self):
        self.backend.upgrade_stylist_account({"specialty": "Smart casual styling", "plan": "pro_monthly"})
        result = self.backend.upgrade_stylist_account({"specialty": "Formal styling", "plan": "pro_annual"})

        state = self.backend.get_state()
        self.assertEqual(len(state["stylistApplications"]), 1)
        self.assertEqual(result["application"]["plan"], "pro_annual")
        self.assertEqual(result["application"]["specialty"], "Formal styling")

    def test_social_post_and_comment_are_persisted(self):
        post_result = self.backend.create_post({"caption": "Testing a clean dinner fit with wardrobe pieces."})
        post_id = post_result["post"]["id"]

        reaction = self.backend.react_to_post(
            {"postId": post_id, "action": "comment", "text": "This works well for dinner."}
        )

        self.assertEqual(reaction["post"]["comments"], 1)
        self.assertEqual(reaction["comment"]["postId"], post_id)

    def test_message_is_persisted(self):
        result = self.backend.send_message({"to": "Tami Looks", "text": "Can you remix this outfit?"})

        self.assertEqual(result["message"]["to"], "Tami Looks")
        self.assertFalse(result["message"]["read"])

    def test_mall_registration_requires_valid_email(self):
        with self.assertRaisesRegex(BackendError, "valid email"):
            self.backend.register_mall({"companyName": "StyleHub", "contactEmail": "not-an-email"})

    def test_mall_registration_is_persisted(self):
        result = self.backend.register_mall(
            {"companyName": "StyleHub", "contactEmail": "owner@stylehub.example", "plan": "starter"}
        )

        self.assertEqual(result["registration"]["status"], "pending_verification")
        self.assertEqual(len(self.backend.get_state()["mallRegistrations"]), 1)

    def test_competition_create_and_submit_entry(self):
        competition = self.backend.create_competition(
            {"name": "Dinner Fit Challenge", "prize": 75, "winnersAllowed": 2, "hoursLeft": 48}
        )["competition"]

        result = self.backend.submit_competition_entry(
            {
                "competitionId": competition["id"],
                "stylistName": "Tami Looks",
                "outfitItems": ["White Oxford Shirt", "Stone Chinos", "White Trainers"],
            }
        )

        self.assertEqual(result["competition"]["stylistsEntered"], 1)
        self.assertEqual(result["entry"]["status"], "submitted")

    def test_follow_stylist_is_idempotent(self):
        self.backend.follow_stylist({"stylistName": "Tami Looks", "action": "follow"})
        result = self.backend.follow_stylist({"stylistName": "Tami Looks", "action": "follow"})

        self.assertEqual(len(result["followers"]), 1)


class FakeSupabaseStore(SupabaseStateStore):
    def __init__(self, rows=None):
        super().__init__("https://example.supabase.co", "service-role-token")
        self.rows = rows or []
        self.requests = []

    def _request(self, method, path, payload=None, extra_headers=None):
        self.requests.append(
            {
                "method": method,
                "path": path,
                "payload": payload,
                "headers": extra_headers or {},
            }
        )
        if method == "GET":
            return self.rows
        if method == "POST":
            self.rows = [{"id": payload[0]["id"], "state": payload[0]["state"]}]
            return self.rows
        raise AssertionError(f"Unexpected method {method}")


class SupabaseStateStoreTests(unittest.TestCase):
    def test_load_seeds_default_state_when_remote_row_is_missing(self):
        store = FakeSupabaseStore()

        state = store.load()

        self.assertEqual(state["profile"]["name"], "Raymond")
        self.assertEqual(store.rows[0]["id"], "production")
        self.assertEqual(store.requests[0]["method"], "GET")
        self.assertEqual(store.requests[1]["method"], "POST")
        self.assertIn("on_conflict=id", store.requests[1]["path"])

    def test_load_migrates_remote_state_without_losing_existing_values(self):
        store = FakeSupabaseStore(rows=[{"state": {"profile": {"role": "stylist"}, "posts": [{"caption": "Old"}]}}])

        state = store.load()

        self.assertEqual(state["profile"]["role"], "stylist")
        self.assertEqual(state["profile"]["name"], "Raymond")
        self.assertEqual(state["posts"][0]["id"], "post_0001")
        self.assertEqual(store.requests[-1]["method"], "POST")


if __name__ == "__main__":
    unittest.main()

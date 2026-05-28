import json
import unittest
from pathlib import Path

from tools.dataset_inventory import validate_registry


ROOT = Path(__file__).resolve().parents[1]


class DatasetRegistryTests(unittest.TestCase):
    def test_approved_datasets_have_license_and_no_synthetic_marker(self):
        registry = json.loads((ROOT / "datasets" / "registry.json").read_text(encoding="utf-8"))

        self.assertEqual(validate_registry(registry), [])

    def test_registry_contains_multiple_training_tasks(self):
        registry = json.loads((ROOT / "datasets" / "registry.json").read_text(encoding="utf-8"))
        tasks = {task for entry in registry["datasets"] for task in entry.get("tasks", [])}

        self.assertIn("image_classification", tasks)
        self.assertIn("object_detection", tasks)
        self.assertIn("virtual_try_on", tasks)
        self.assertIn("recommendation", tasks)


if __name__ == "__main__":
    unittest.main()

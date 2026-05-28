#!/usr/bin/env python3
"""Train SwitchAI preference priors from real saved app feedback exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ACTION_WEIGHT = {"love": 3, "like": 2, "dislike": -2}


def load_state(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def train_priors(states: list[dict[str, Any]]) -> dict[str, Any]:
    colors: dict[str, int] = {}
    categories: dict[str, int] = {}
    materials: dict[str, int] = {}
    examples = 0
    for state in states:
        wardrobe = {item.get("name"): item for item in state.get("wardrobe", [])}
        for feedback in state.get("switchAi", {}).get("feedback", []):
            action = feedback.get("action")
            if action not in ACTION_WEIGHT:
                continue
            examples += 1
            weight = ACTION_WEIGHT[action]
            for name in feedback.get("outfitItems", []):
                item = wardrobe.get(name)
                if not item:
                    continue
                bump(colors, str(item.get("color", item.get("colorName", "custom"))), weight)
                bump(categories, str(item.get("category", "custom")), weight)
                bump(materials, str(item.get("material", "custom")), weight)
    return {
        "model": "SwitchAI feedback prior ranker",
        "trained_at": "2026-05-28",
        "training_examples": examples,
        "preferences": {
            "colors": colors,
            "categories": categories,
            "materials": materials,
            "formalityBias": 0,
        },
    }


def bump(values: dict[str, int], key: str, weight: int) -> None:
    values[key] = values.get(key, 0) + weight


def main() -> int:
    parser = argparse.ArgumentParser(description="Train SwitchAI preference priors from exported state JSON.")
    parser.add_argument("--state", action="append", type=Path, required=True, help="Path to a real Switch It Up state JSON export.")
    parser.add_argument("--output", type=Path, default=Path("models/switchai-priors.json"))
    args = parser.parse_args()

    missing = [str(path) for path in args.state if not path.exists()]
    if missing:
        print(json.dumps({"ok": False, "error": "missing_state_files", "missing": missing}, indent=2))
        return 1

    model = train_priors([load_state(path) for path in args.state])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output), "training_examples": model["training_examples"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""CSV report helpers for SwitchItUp."""

from __future__ import annotations

import csv
from pathlib import Path

from .style_engine import build_style_plan, sample_request, sample_stylists, sample_wardrobe


def export_sample_report(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    plan = build_style_plan(sample_wardrobe(), sample_stylists(), sample_request())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "outfit_items",
                "missing_categories",
                "replacement_suggestions",
                "recommended_stylists",
                "confidence_percent",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "outfit_items": ", ".join(plan.outfit_items),
                "missing_categories": ", ".join(plan.missing_categories) or "None",
                "replacement_suggestions": " | ".join(plan.replacement_suggestions) or "None",
                "recommended_stylists": ", ".join(plan.recommended_stylists),
                "confidence_percent": plan.confidence_percent,
            }
        )
    return path

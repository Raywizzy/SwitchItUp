#!/usr/bin/env python3
"""Inspect SwitchAI dataset registry entries against Hugging Face metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "datasets" / "registry.json"
DATASETS_SERVER = "https://datasets-server.huggingface.co"


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def hf_get(endpoint: str, **params) -> dict:
    url = f"{DATASETS_SERVER}/{endpoint}?{urlencode(params)}"
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def inspect_dataset(entry: dict) -> dict:
    result = {
        "id": entry["id"],
        "repo_id": entry.get("repo_id"),
        "status": entry.get("status"),
        "license": entry.get("license"),
        "tasks": entry.get("tasks", []),
        "registry_rows": entry.get("rows"),
        "registry_bytes": entry.get("bytes"),
        "viewer_ok": False,
        "splits": [],
        "rows": None,
        "bytes": None,
        "error": None,
    }
    if entry.get("source") != "huggingface" or not entry.get("repo_id"):
        result["error"] = "Only Hugging Face dataset entries are supported."
        return result
    try:
        size = hf_get("size", dataset=entry["repo_id"])
        result["viewer_ok"] = True
        result["rows"] = size.get("size", {}).get("dataset", {}).get("num_rows")
        result["bytes"] = size.get("size", {}).get("dataset", {}).get("num_bytes_parquet_files")
        result["splits"] = [
            {
                "config": split.get("config"),
                "split": split.get("split"),
                "rows": split.get("num_rows"),
                "bytes": split.get("num_bytes_parquet_files"),
            }
            for split in size.get("size", {}).get("splits", [])
        ]
    except Exception as exc:  # Network/API errors are reported, not hidden.
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def validate_registry(registry: dict) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    for entry in registry.get("datasets", []):
        dataset_id = entry.get("id")
        if not dataset_id:
            errors.append("dataset entry missing id")
            continue
        if dataset_id in ids:
            errors.append(f"duplicate dataset id: {dataset_id}")
        ids.add(dataset_id)
        if entry.get("status") == "approved":
            if not entry.get("license"):
                errors.append(f"{dataset_id} is approved but has no license")
            notes = " ".join(str(value).lower() for value in entry.values())
            if "synthetic" in notes:
                errors.append(f"{dataset_id} is approved but mentions synthetic data")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect SwitchAI training dataset registry.")
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--approved-only", action="store_true")
    parser.add_argument("--write", type=Path, help="Optional JSON report output path.")
    args = parser.parse_args()

    registry = load_registry(args.registry)
    errors = validate_registry(registry)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1

    entries = registry.get("datasets", [])
    if args.approved_only:
        entries = [entry for entry in entries if entry.get("status") == "approved"]
    report = {
        "ok": True,
        "generated_at": registry.get("generated_at"),
        "datasets": [inspect_dataset(entry) for entry in entries],
    }
    payload = json.dumps(report, indent=2)
    print(payload)
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

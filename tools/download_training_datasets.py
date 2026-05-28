#!/usr/bin/env python3
"""Download approved Hugging Face parquet shards for SwitchAI training.

The script is deliberately conservative: by default it prints a dry-run plan.
Use --execute to download, and use --max-shards to keep local storage sane.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "datasets" / "registry.json"
DATASETS_SERVER = "https://datasets-server.huggingface.co"
RAW_ROOT = ROOT / "datasets" / "raw"


def load_registry() -> dict:
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def hf_get(endpoint: str, **params) -> dict:
    url = f"{DATASETS_SERVER}/{endpoint}?{urlencode(params)}"
    with urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def parquet_files(repo_id: str) -> list[dict]:
    payload = hf_get("parquet", dataset=repo_id)
    return payload.get("parquet_files", [])


def selected_entries(registry: dict, dataset_ids: list[str], include_review_required: bool) -> list[dict]:
    entries = registry.get("datasets", [])
    if dataset_ids:
        wanted = set(dataset_ids)
        entries = [entry for entry in entries if entry.get("id") in wanted]
    if not include_review_required:
        entries = [entry for entry in entries if entry.get("status") == "approved"]
    return entries


def download(url: str, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with urlopen(url, timeout=60) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            handle.write(chunk)
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Download approved SwitchAI training datasets.")
    parser.add_argument("--dataset", action="append", default=[], help="Dataset id from datasets/registry.json.")
    parser.add_argument("--include-review-required", action="store_true")
    parser.add_argument("--max-shards", type=int, default=1, help="Maximum parquet shards per dataset.")
    parser.add_argument("--execute", action="store_true", help="Actually download files. Omit for dry-run.")
    parser.add_argument("--raw-root", type=Path, default=RAW_ROOT)
    args = parser.parse_args()

    registry = load_registry()
    plan = []
    for entry in selected_entries(registry, args.dataset, args.include_review_required):
        if entry.get("source") != "huggingface" or not entry.get("repo_id"):
            continue
        if entry.get("status") != "approved" and not args.include_review_required:
            continue
        try:
            shards = parquet_files(entry["repo_id"])
        except Exception as exc:
            plan.append({"id": entry["id"], "repo_id": entry["repo_id"], "error": f"{type(exc).__name__}: {exc}"})
            continue
        for shard in shards[: max(args.max_shards, 0)]:
            filename = shard.get("filename", "data.parquet")
            url = shard.get("url")
            destination = args.raw_root / entry["id"] / str(shard.get("config", "default")) / str(shard.get("split", "data")) / filename
            item = {
                "id": entry["id"],
                "repo_id": entry["repo_id"],
                "license": entry.get("license"),
                "status": entry.get("status"),
                "split": shard.get("split"),
                "filename": filename,
                "destination": str(destination),
                "url": url,
                "downloaded_bytes": 0,
            }
            if args.execute:
                if not url:
                    item["error"] = "missing parquet URL"
                else:
                    item["downloaded_bytes"] = download(url, destination)
            plan.append(item)
    print(json.dumps({"execute": args.execute, "max_shards": args.max_shards, "plan": plan}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

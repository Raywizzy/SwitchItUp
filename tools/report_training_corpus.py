#!/usr/bin/env python3
"""Report local SwitchAI training corpus files without reading them into memory."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "datasets" / "registry.json"
RAW_ROOT = ROOT / "datasets" / "raw"


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_registry(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def files_for_dataset(raw_root: Path, dataset_id: str) -> list[dict]:
    dataset_root = raw_root / dataset_id
    if not dataset_root.exists():
        return []
    rows = []
    for path in sorted(dataset_root.rglob("*")):
        if path.is_file():
            rows.append(
                {
                    "path": str(path),
                    "relative_path": str(path.relative_to(raw_root)),
                    "bytes": path.stat().st_size,
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Report downloaded SwitchAI training corpus files.")
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--raw-root", type=Path, default=RAW_ROOT)
    parser.add_argument("--write", type=Path, help="Optional JSON report output path.")
    args = parser.parse_args()

    registry = load_registry(args.registry)
    datasets = []
    total_bytes = 0
    total_files = 0
    for entry in registry.get("datasets", []):
        files = files_for_dataset(args.raw_root, entry["id"])
        bytes_for_dataset = sum(item["bytes"] for item in files)
        total_bytes += bytes_for_dataset
        total_files += len(files)
        datasets.append(
            {
                "id": entry["id"],
                "name": entry.get("name"),
                "repo_id": entry.get("repo_id"),
                "status": entry.get("status"),
                "license": entry.get("license"),
                "tasks": entry.get("tasks", []),
                "downloaded_files": len(files),
                "downloaded_bytes": bytes_for_dataset,
                "files": files,
            }
        )

    report = {
        "ok": True,
        "generated_at": iso_now(),
        "raw_root": str(args.raw_root),
        "total_files": total_files,
        "total_bytes": total_bytes,
        "datasets": datasets,
    }
    payload = json.dumps(report, indent=2)
    print(payload)
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

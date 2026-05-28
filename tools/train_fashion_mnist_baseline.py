#!/usr/bin/env python3
"""Train a deterministic Fashion-MNIST baseline with only the Python stdlib."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import platform
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "datasets" / "raw" / "fashion_mnist_idx"
MODEL_PATH = ROOT / "models" / "switchai-fashion-mnist-centroids.json"
REPORT_DIR = ROOT / "reports" / "training" / "fashion_mnist_baseline"
SOURCE_BASE_URL = "https://raw.githubusercontent.com/zalandoresearch/fashion-mnist/master/data/fashion"
LABELS = [
    "T-shirt/top",
    "Trouser",
    "Pullover",
    "Dress",
    "Coat",
    "Sandal",
    "Shirt",
    "Sneaker",
    "Bag",
    "Ankle boot",
]
FILES = {
    "train_images": "train-images-idx3-ubyte.gz",
    "train_labels": "train-labels-idx1-ubyte.gz",
    "test_images": "t10k-images-idx3-ubyte.gz",
    "test_labels": "t10k-labels-idx1-ubyte.gz",
}


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def download_if_needed(filename: str, raw_root: Path) -> Path:
    destination = raw_root / filename
    if destination.exists():
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = f"{SOURCE_BASE_URL}/{filename}"
    try:
        with urlopen(url, timeout=60) as response, destination.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    except Exception as exc:
        if destination.exists():
            destination.unlink()
        raise RuntimeError(f"failed to download {url}: {type(exc).__name__}: {exc}") from exc
    return destination


def read_idx_images(path: Path, limit: int | None) -> tuple[bytes, int, int, int]:
    with gzip.open(path, "rb") as handle:
        magic, count, rows, cols = struct.unpack(">IIII", handle.read(16))
        if magic != 2051:
            raise ValueError(f"{path} has invalid image IDX magic {magic}")
        selected = min(count, limit) if limit else count
        pixels = rows * cols
        data = handle.read(selected * pixels)
        if len(data) != selected * pixels:
            raise ValueError(f"{path} ended early while reading images")
    return data, selected, rows, cols


def read_idx_labels(path: Path, limit: int | None) -> list[int]:
    with gzip.open(path, "rb") as handle:
        magic, count = struct.unpack(">II", handle.read(8))
        if magic != 2049:
            raise ValueError(f"{path} has invalid label IDX magic {magic}")
        selected = min(count, limit) if limit else count
        labels = list(handle.read(selected))
        if len(labels) != selected:
            raise ValueError(f"{path} ended early while reading labels")
    unknown = sorted({label for label in labels if label < 0 or label >= len(LABELS)})
    if unknown:
        raise ValueError(f"{path} includes unknown labels: {unknown}")
    return labels


def train_centroids(images: bytes, labels: list[int], rows: int, cols: int) -> tuple[list[list[float]], list[int]]:
    pixels = rows * cols
    sums = [[0.0] * pixels for _ in LABELS]
    counts = [0] * len(LABELS)
    for index, label in enumerate(labels):
        counts[label] += 1
        start = index * pixels
        image = images[start : start + pixels]
        target = sums[label]
        for pixel_index, value in enumerate(image):
            target[pixel_index] += value
    missing = [LABELS[index] for index, count in enumerate(counts) if count == 0]
    if missing:
        raise ValueError(f"training subset has no examples for classes: {', '.join(missing)}")
    centroids = [[value / counts[label] for value in sums[label]] for label in range(len(LABELS))]
    return centroids, counts


def predict(image: bytes, centroids: list[list[float]], centroid_norms: list[float]) -> int:
    best_label = 0
    best_score = math.inf
    for label, centroid in enumerate(centroids):
        score = centroid_norms[label]
        for pixel, mean in zip(image, centroid):
            score -= 2.0 * pixel * mean
        if score < best_score:
            best_score = score
            best_label = label
    return best_label


def evaluate(images: bytes, labels: list[int], rows: int, cols: int, centroids: list[list[float]]) -> dict:
    pixels = rows * cols
    confusion = [[0 for _ in LABELS] for _ in LABELS]
    centroid_norms = [sum(value * value for value in centroid) for centroid in centroids]
    for index, actual in enumerate(labels):
        start = index * pixels
        predicted = predict(images[start : start + pixels], centroids, centroid_norms)
        confusion[actual][predicted] += 1
    total = sum(sum(row) for row in confusion)
    correct = sum(confusion[index][index] for index in range(len(LABELS)))
    per_class = []
    for index, row in enumerate(confusion):
        class_total = sum(row)
        class_correct = row[index]
        per_class.append(
            {
                "label": LABELS[index],
                "support": class_total,
                "correct": class_correct,
                "accuracy": class_correct / class_total if class_total else 0.0,
            }
        )
    return {
        "accuracy": correct / total if total else 0.0,
        "correct": correct,
        "total": total,
        "per_class": per_class,
        "confusion_matrix": confusion,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_confusion_csv(path: Path, confusion: list[list[int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["actual/predicted", *LABELS])
        for label, row in zip(LABELS, confusion):
            writer.writerow([label, *row])


def write_accuracy_svg(path: Path, per_class: list[dict]) -> None:
    width = 980
    height = 460
    left = 90
    top = 50
    chart_width = 820
    chart_height = 300
    bar_width = chart_width / len(per_class)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfbfd"/>',
        '<text x="42" y="34" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="20" font-weight="700" fill="#1d1d1f">Fashion-MNIST Baseline Accuracy by Class</text>',
        f'<line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" y2="{top + chart_height}" stroke="#86868b"/>',
    ]
    for index, item in enumerate(per_class):
        rate = item["accuracy"]
        x = left + index * bar_width + 12
        bar_height = rate * chart_height
        y = top + chart_height - bar_height
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width - 24:.1f}" height="{bar_height:.1f}" rx="8" fill="#0071e3"/>')
        parts.append(f'<text x="{x + (bar_width - 24) / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="12" fill="#1d1d1f">{rate:.1%}</text>')
        label = item["label"].replace("&", "&amp;")
        parts.append(f'<text x="{x + (bar_width - 24) / 2:.1f}" y="{top + chart_height + 24}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="11" fill="#424245">{label}</text>')
    parts.append('<text x="42" y="430" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13" fill="#6e6e73">Model: nearest class centroid over real Fashion-MNIST pixels. Higher is better.</text>')
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def write_confusion_svg(path: Path, confusion: list[list[int]]) -> None:
    cell = 46
    left = 190
    top = 72
    width = left + cell * len(LABELS) + 32
    height = top + cell * len(LABELS) + 72
    max_value = max(max(row) for row in confusion) or 1
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfbfd"/>',
        '<text x="32" y="34" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="20" font-weight="700" fill="#1d1d1f">Fashion-MNIST Confusion Matrix</text>',
    ]
    for index, label in enumerate(LABELS):
        safe_label = label.replace("&", "&amp;")
        parts.append(f'<text x="{left + index * cell + cell / 2}" y="62" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="9" fill="#424245" transform="rotate(-35 {left + index * cell + cell / 2} 62)">{safe_label}</text>')
        parts.append(f'<text x="{left - 12}" y="{top + index * cell + cell / 2 + 4}" text-anchor="end" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="11" fill="#424245">{safe_label}</text>')
    for row_index, row in enumerate(confusion):
        for col_index, value in enumerate(row):
            intensity = value / max_value
            blue = int(236 - intensity * 156)
            fill = f"rgb({blue},{blue + 12},255)"
            x = left + col_index * cell
            y = top + row_index * cell
            text_color = "#ffffff" if intensity > 0.48 else "#1d1d1f"
            parts.append(f'<rect x="{x}" y="{y}" width="{cell - 2}" height="{cell - 2}" rx="6" fill="{fill}"/>')
            parts.append(f'<text x="{x + cell / 2}" y="{y + cell / 2 + 4}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="11" fill="{text_color}">{value}</text>')
    parts.append('<text x="32" y="{0}" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13" fill="#6e6e73">Rows are actual labels; columns are predicted labels.</text>'.format(height - 24))
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a real Fashion-MNIST baseline for SwitchAI.")
    parser.add_argument("--raw-root", type=Path, default=RAW_ROOT)
    parser.add_argument("--model-output", type=Path, default=MODEL_PATH)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--max-train", type=int, default=60000)
    parser.add_argument("--max-eval", type=int, default=10000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = iso_now()
    print(json.dumps({"event": "start", "started_at": started_at, "python": sys.version.split()[0], "platform": platform.platform()}, indent=2))
    paths = {name: download_if_needed(filename, args.raw_root) for name, filename in FILES.items()}
    train_images, train_count, rows, cols = read_idx_images(paths["train_images"], args.max_train)
    train_labels = read_idx_labels(paths["train_labels"], args.max_train)
    test_images, test_count, test_rows, test_cols = read_idx_images(paths["test_images"], args.max_eval)
    test_labels = read_idx_labels(paths["test_labels"], args.max_eval)
    if (rows, cols) != (test_rows, test_cols):
        raise ValueError("train/test image dimensions do not match")
    if train_count != len(train_labels) or test_count != len(test_labels):
        raise ValueError("image and label counts do not match")

    centroids, class_counts = train_centroids(train_images, train_labels, rows, cols)
    metrics = evaluate(test_images, test_labels, rows, cols, centroids)
    finished_at = iso_now()

    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    model = {
        "model": "SwitchAI nearest-centroid Fashion-MNIST baseline",
        "dataset": "Fashion-MNIST",
        "source_url": SOURCE_BASE_URL,
        "license": "MIT",
        "trained_at": finished_at,
        "deterministic": True,
        "seed": None,
        "image_shape": [rows, cols],
        "labels": LABELS,
        "class_counts": class_counts,
        "centroids": centroids,
    }
    args.model_output.write_text(json.dumps(model) + "\n", encoding="utf-8")

    report = {
        "ok": True,
        "started_at": started_at,
        "finished_at": finished_at,
        "python": sys.version,
        "platform": platform.platform(),
        "dataset": {
            "name": "Fashion-MNIST",
            "source_url": SOURCE_BASE_URL,
            "license": "MIT",
            "train_examples": train_count,
            "eval_examples": test_count,
            "labels": LABELS,
        },
        "model_output": str(args.model_output),
        "metrics": metrics,
        "artifacts": {
            "metrics_json": str(args.report_dir / "metrics.json"),
            "accuracy_by_class_csv": str(args.report_dir / "accuracy_by_class.csv"),
            "confusion_matrix_csv": str(args.report_dir / "confusion_matrix.csv"),
            "accuracy_by_class_svg": str(args.report_dir / "accuracy_by_class.svg"),
            "confusion_matrix_svg": str(args.report_dir / "confusion_matrix.svg"),
        },
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "metrics.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_csv(args.report_dir / "accuracy_by_class.csv", metrics["per_class"])
    write_confusion_csv(args.report_dir / "confusion_matrix.csv", metrics["confusion_matrix"])
    write_accuracy_svg(args.report_dir / "accuracy_by_class.svg", metrics["per_class"])
    write_confusion_svg(args.report_dir / "confusion_matrix.svg", metrics["confusion_matrix"])
    print(json.dumps({"event": "finished", "accuracy": metrics["accuracy"], "correct": metrics["correct"], "total": metrics["total"], "report_dir": str(args.report_dir), "model_output": str(args.model_output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

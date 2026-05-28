#!/usr/bin/env python3
"""Train a deterministic NumPy softmax classifier on real Fashion-MNIST data."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import platform
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "datasets" / "raw" / "fashion_mnist_idx"
MODEL_PATH = ROOT / "models" / "switchai-fashion-mnist-softmax.npz"
REPORT_DIR = ROOT / "reports" / "training" / "fashion_mnist_softmax"
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


def require_numpy():
    try:
        import numpy as np
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing training library: numpy\n"
            "Remediation: run with the bundled Python runtime or install numpy in a virtualenv."
        ) from exc
    return np


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


def read_idx_images(path: Path, limit: int | None, np):
    with gzip.open(path, "rb") as handle:
        magic, count, rows, cols = struct.unpack(">IIII", handle.read(16))
        if magic != 2051:
            raise ValueError(f"{path} has invalid image IDX magic {magic}")
        selected = min(count, limit) if limit else count
        pixels = rows * cols
        data = handle.read(selected * pixels)
        if len(data) != selected * pixels:
            raise ValueError(f"{path} ended early while reading images")
    images = np.frombuffer(data, dtype=np.uint8).reshape(selected, pixels).astype(np.float32) / 255.0
    return images, rows, cols


def read_idx_labels(path: Path, limit: int | None, np):
    with gzip.open(path, "rb") as handle:
        magic, count = struct.unpack(">II", handle.read(8))
        if magic != 2049:
            raise ValueError(f"{path} has invalid label IDX magic {magic}")
        selected = min(count, limit) if limit else count
        data = handle.read(selected)
        if len(data) != selected:
            raise ValueError(f"{path} ended early while reading labels")
    labels = np.frombuffer(data, dtype=np.uint8).astype(np.int64)
    unknown = sorted(int(label) for label in set(labels.tolist()) if label < 0 or label >= len(LABELS))
    if unknown:
        raise ValueError(f"{path} includes unknown labels: {unknown}")
    return labels


def softmax(logits, np):
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def accuracy(x, y, weights, bias) -> float:
    predictions = (x @ weights + bias).argmax(axis=1)
    return float((predictions == y).mean())


def evaluate(x, y, weights, bias, np) -> dict:
    predictions = (x @ weights + bias).argmax(axis=1)
    confusion = np.zeros((len(LABELS), len(LABELS)), dtype=np.int64)
    for actual, predicted in zip(y, predictions):
        confusion[int(actual), int(predicted)] += 1
    total = int(confusion.sum())
    correct = int(np.trace(confusion))
    per_class = []
    for index, label in enumerate(LABELS):
        support = int(confusion[index].sum())
        class_correct = int(confusion[index, index])
        per_class.append(
            {
                "label": label,
                "support": support,
                "correct": class_correct,
                "accuracy": class_correct / support if support else 0.0,
            }
        )
    return {
        "accuracy": correct / total if total else 0.0,
        "correct": correct,
        "total": total,
        "per_class": per_class,
        "confusion_matrix": confusion.tolist(),
    }


def train_softmax(train_x, train_y, eval_x, eval_y, args, np) -> tuple:
    rng = np.random.default_rng(args.seed)
    sample_count, feature_count = train_x.shape
    class_count = len(LABELS)
    weights = rng.normal(0.0, 0.01, size=(feature_count, class_count)).astype(np.float32)
    bias = np.zeros(class_count, dtype=np.float32)
    history = []

    for epoch in range(1, args.epochs + 1):
        order = rng.permutation(sample_count)
        losses = []
        for start in range(0, sample_count, args.batch_size):
            batch_indices = order[start : start + args.batch_size]
            x_batch = train_x[batch_indices]
            y_batch = train_y[batch_indices]
            probabilities = softmax(x_batch @ weights + bias, np)
            losses.append(float(-np.log(probabilities[np.arange(len(y_batch)), y_batch] + 1e-9).mean()))
            probabilities[np.arange(len(y_batch)), y_batch] -= 1.0
            probabilities /= len(y_batch)
            weights -= args.learning_rate * (x_batch.T @ probabilities + args.weight_decay * weights)
            bias -= args.learning_rate * probabilities.sum(axis=0)
        item = {
            "epoch": epoch,
            "loss": float(np.mean(losses)),
            "train_accuracy": accuracy(train_x, train_y, weights, bias),
            "eval_accuracy": accuracy(eval_x, eval_y, weights, bias),
        }
        history.append(item)
        print(json.dumps(item))
    return weights, bias, history


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


def line_svg(path: Path, history: list[dict]) -> None:
    width = 920
    height = 460
    left = 72
    top = 54
    chart_width = 780
    chart_height = 300
    max_epoch = max(item["epoch"] for item in history)
    min_loss = min(item["loss"] for item in history)
    max_loss = max(item["loss"] for item in history)

    def x(epoch: int) -> float:
        if max_epoch == 1:
            return left + chart_width
        return left + ((epoch - 1) / (max_epoch - 1)) * chart_width

    def y_accuracy(value: float) -> float:
        return top + chart_height - value * chart_height

    def y_loss(value: float) -> float:
        spread = max(max_loss - min_loss, 1e-6)
        return top + chart_height - ((value - min_loss) / spread) * chart_height

    eval_points = " ".join(f'{x(item["epoch"]):.1f},{y_accuracy(item["eval_accuracy"]):.1f}' for item in history)
    train_points = " ".join(f'{x(item["epoch"]):.1f},{y_accuracy(item["train_accuracy"]):.1f}' for item in history)
    loss_points = " ".join(f'{x(item["epoch"]):.1f},{y_loss(item["loss"]):.1f}' for item in history)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfbfd"/>',
        '<text x="38" y="34" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="20" font-weight="700" fill="#1d1d1f">Fashion-MNIST Softmax Training</text>',
        f'<line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" y2="{top + chart_height}" stroke="#86868b"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" stroke="#86868b"/>',
        f'<polyline points="{train_points}" fill="none" stroke="#34c759" stroke-width="3"/>',
        f'<polyline points="{eval_points}" fill="none" stroke="#0071e3" stroke-width="3"/>',
        f'<polyline points="{loss_points}" fill="none" stroke="#ff9500" stroke-width="3" stroke-dasharray="8 6"/>',
        '<circle cx="690" cy="28" r="5" fill="#34c759"/><text x="704" y="33" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="12" fill="#1d1d1f">Train accuracy</text>',
        '<circle cx="690" cy="50" r="5" fill="#0071e3"/><text x="704" y="55" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="12" fill="#1d1d1f">Eval accuracy</text>',
        '<circle cx="690" cy="72" r="5" fill="#ff9500"/><text x="704" y="77" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="12" fill="#1d1d1f">Loss trend</text>',
    ]
    for item in history:
        parts.append(f'<text x="{x(item["epoch"]):.1f}" y="{top + chart_height + 24}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="11" fill="#424245">{item["epoch"]}</text>')
    parts.append('<text x="38" y="430" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13" fill="#6e6e73">Solid lines use the accuracy scale. Orange dashed line shows loss normalized to its observed range.</text>')
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def bar_svg(path: Path, per_class: list[dict]) -> None:
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
        '<text x="42" y="34" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="20" font-weight="700" fill="#1d1d1f">Softmax Accuracy by Class</text>',
        f'<line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" y2="{top + chart_height}" stroke="#86868b"/>',
    ]
    for index, item in enumerate(per_class):
        rate = item["accuracy"]
        x = left + index * bar_width + 12
        bar_height = rate * chart_height
        y = top + chart_height - bar_height
        label = item["label"].replace("&", "&amp;")
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width - 24:.1f}" height="{bar_height:.1f}" rx="8" fill="#0071e3"/>')
        parts.append(f'<text x="{x + (bar_width - 24) / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="12" fill="#1d1d1f">{rate:.1%}</text>')
        parts.append(f'<text x="{x + (bar_width - 24) / 2:.1f}" y="{top + chart_height + 24}" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="11" fill="#424245">{label}</text>')
    parts.append('<text x="42" y="430" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="13" fill="#6e6e73">Real Fashion-MNIST test split. Higher is better.</text>')
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a NumPy softmax classifier on real Fashion-MNIST.")
    parser.add_argument("--raw-root", type=Path, default=RAW_ROOT)
    parser.add_argument("--model-output", type=Path, default=MODEL_PATH)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--max-train", type=int, default=60000)
    parser.add_argument("--max-eval", type=int, default=10000)
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=0.18)
    parser.add_argument("--weight-decay", type=float, default=0.0005)
    parser.add_argument("--seed", type=int, default=20260528)
    return parser.parse_args()


def main() -> int:
    np = require_numpy()
    args = parse_args()
    started_at = iso_now()
    print(
        json.dumps(
            {
                "event": "start",
                "started_at": started_at,
                "python": sys.version.split()[0],
                "numpy": np.__version__,
                "platform": platform.platform(),
                "seed": args.seed,
            },
            indent=2,
        )
    )
    paths = {name: download_if_needed(filename, args.raw_root) for name, filename in FILES.items()}
    train_x, rows, cols = read_idx_images(paths["train_images"], args.max_train, np)
    train_y = read_idx_labels(paths["train_labels"], args.max_train, np)
    eval_x, eval_rows, eval_cols = read_idx_images(paths["test_images"], args.max_eval, np)
    eval_y = read_idx_labels(paths["test_labels"], args.max_eval, np)
    if (rows, cols) != (eval_rows, eval_cols):
        raise ValueError("train/test image dimensions do not match")
    if len(train_x) != len(train_y) or len(eval_x) != len(eval_y):
        raise ValueError("image and label counts do not match")

    weights, bias, history = train_softmax(train_x, train_y, eval_x, eval_y, args, np)
    metrics = evaluate(eval_x, eval_y, weights, bias, np)
    finished_at = iso_now()

    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.model_output,
        weights=weights,
        bias=bias,
        labels=np.array(LABELS),
        image_shape=np.array([rows, cols]),
    )

    report = {
        "ok": True,
        "started_at": started_at,
        "finished_at": finished_at,
        "python": sys.version,
        "numpy": np.__version__,
        "platform": platform.platform(),
        "seed": args.seed,
        "dataset": {
            "name": "Fashion-MNIST",
            "source_url": SOURCE_BASE_URL,
            "license": "MIT",
            "train_examples": int(len(train_x)),
            "eval_examples": int(len(eval_x)),
            "labels": LABELS,
        },
        "training": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "weight_decay": args.weight_decay,
        },
        "model_output": str(args.model_output),
        "history": history,
        "metrics": metrics,
        "artifacts": {
            "metrics_json": str(args.report_dir / "metrics.json"),
            "history_csv": str(args.report_dir / "history.csv"),
            "accuracy_by_class_csv": str(args.report_dir / "accuracy_by_class.csv"),
            "confusion_matrix_csv": str(args.report_dir / "confusion_matrix.csv"),
            "training_curve_svg": str(args.report_dir / "training_curve.svg"),
            "accuracy_by_class_svg": str(args.report_dir / "accuracy_by_class.svg"),
        },
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "metrics.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_csv(args.report_dir / "history.csv", history)
    write_csv(args.report_dir / "accuracy_by_class.csv", metrics["per_class"])
    write_confusion_csv(args.report_dir / "confusion_matrix.csv", metrics["confusion_matrix"])
    line_svg(args.report_dir / "training_curve.svg", history)
    bar_svg(args.report_dir / "accuracy_by_class.svg", metrics["per_class"])
    print(
        json.dumps(
            {
                "event": "finished",
                "accuracy": metrics["accuracy"],
                "correct": metrics["correct"],
                "total": metrics["total"],
                "report_dir": str(args.report_dir),
                "model_output": str(args.model_output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

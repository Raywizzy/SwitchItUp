#!/usr/bin/env python3
# /// script
# dependencies = [
#   "datasets>=2.20.0",
#   "transformers>=4.44.0",
#   "torch>=2.3.0",
#   "torchvision>=0.18.0",
#   "evaluate>=0.4.2",
#   "pillow>=10.4.0",
#   "scikit-learn>=1.5.0",
#   "accelerate>=0.33.0"
# ]
# ///
"""Fine-tune a real clothing image classifier for SwitchAI.

Recommended first run:
uv run tools/train_switch_ai_vision.py \
  --dataset zalando-datasets/fashion_mnist \
  --config fashion_mnist \
  --train-split train \
  --eval-split test \
  --max-train-samples 2000 \
  --max-eval-samples 500 \
  --epochs 1 \
  --output-dir models/switchai-fashion-mnist-smoke
"""

from __future__ import annotations

import argparse
from pathlib import Path


def require_training_deps():
    missing = []
    modules = {
        "datasets": "datasets",
        "transformers": "transformers",
        "torch": "torch",
        "evaluate": "evaluate",
        "PIL": "pillow",
    }
    loaded = {}
    for module, package in modules.items():
        try:
            loaded[module] = __import__(module)
        except ModuleNotFoundError:
            missing.append(package)
    if missing:
        raise SystemExit(
            "Missing training libraries: "
            + ", ".join(sorted(set(missing)))
            + "\nRemediation: run with `uv run tools/train_switch_ai_vision.py ...` or install them in a virtualenv."
        )
    return loaded


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train SwitchAI clothing vision classifier.")
    parser.add_argument("--dataset", default="zalando-datasets/fashion_mnist")
    parser.add_argument("--config", default="fashion_mnist")
    parser.add_argument("--train-split", default="train")
    parser.add_argument("--eval-split", default="test")
    parser.add_argument("--image-column", default="image")
    parser.add_argument("--label-column", default="label")
    parser.add_argument("--model", default="google/vit-base-patch16-224-in21k")
    parser.add_argument("--output-dir", default="models/switchai-vision")
    parser.add_argument("--max-train-samples", type=int, default=2000)
    parser.add_argument("--max-eval-samples", type=int, default=500)
    parser.add_argument("--epochs", type=float, default=1)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    parser.add_argument("--seed", type=int, default=20260528)
    return parser.parse_args()


def main() -> int:
    require_training_deps()
    from datasets import load_dataset
    import evaluate
    import numpy as np
    import torch
    from transformers import AutoImageProcessor, AutoModelForImageClassification, Trainer, TrainingArguments

    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    train_ds = load_dataset(args.dataset, args.config, split=args.train_split)
    eval_ds = load_dataset(args.dataset, args.config, split=args.eval_split)
    if args.max_train_samples:
        train_ds = train_ds.shuffle(seed=args.seed).select(range(min(args.max_train_samples, len(train_ds))))
    if args.max_eval_samples:
        eval_ds = eval_ds.shuffle(seed=args.seed).select(range(min(args.max_eval_samples, len(eval_ds))))

    feature = train_ds.features[args.label_column]
    if hasattr(feature, "names") and feature.names:
        label_names = list(feature.names)
    else:
        label_names = sorted({str(value) for value in train_ds[args.label_column]})
    label2id = {name: index for index, name in enumerate(label_names)}
    id2label = {index: name for name, index in label2id.items()}

    processor = AutoImageProcessor.from_pretrained(args.model)

    def normalize_label(value):
        if isinstance(value, int):
            return value
        return label2id[str(value)]

    def transform(batch):
        images = [image.convert("RGB") for image in batch[args.image_column]]
        encoded = processor(images, return_tensors="pt")
        encoded["labels"] = [normalize_label(label) for label in batch[args.label_column]]
        return encoded

    train_ds = train_ds.with_transform(transform)
    eval_ds = eval_ds.with_transform(transform)
    accuracy = evaluate.load("accuracy")

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)
        return accuracy.compute(predictions=predictions, references=labels)

    model = AutoModelForImageClassification.from_pretrained(
        args.model,
        num_labels=len(label_names),
        id2label=id2label,
        label2id=label2id,
        ignore_mismatched_sizes=True,
    )

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        remove_unused_columns=False,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        seed=args.seed,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        tokenizer=processor,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    metrics = trainer.evaluate()
    trainer.save_model(str(output_dir / "model"))
    processor.save_pretrained(str(output_dir / "model"))
    (output_dir / "metrics.json").write_text(__import__("json").dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

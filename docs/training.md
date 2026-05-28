# SwitchAI Training Plan

Date: 2026-05-28

SwitchAI training uses only real datasets listed in `datasets/registry.json`.
Datasets marked `review_required` are not used by default.

## Dataset Layers

- Starter classifier: `zalando-datasets/fashion_mnist`
- Clothing detector: `detection-datasets/fashionpedia_4_categories`
- Fine-grained detector and attributes: `detection-datasets/fashionpedia`
- Image/text fashion search: `Marqo/fashion200k`
- Outfit and virtual try-on research: `ArtmeScienceLab/Garments2Look`
- Garment condition checks: Wargön Innovation condition datasets

## Inspect Dataset Metadata

```bash
python3 tools/dataset_inventory.py --approved-only
```

Write a local report:

```bash
python3 tools/dataset_inventory.py --approved-only --write reports/dataset_inventory.json
```

## Download Data

Dry run:

```bash
python3 tools/download_training_datasets.py --dataset fashion_mnist --max-shards 1
```

Download one shard:

```bash
python3 tools/download_training_datasets.py --dataset fashion_mnist --max-shards 1 --execute
```

Downloaded data goes under `datasets/raw/`, which is ignored by git.

## Train Vision Classifier

Dependency-free baseline using the real Fashion-MNIST IDX files:

```bash
python3 tools/train_fashion_mnist_baseline.py
```

This writes:

- `models/switchai-fashion-mnist-centroids.json`
- `reports/training/fashion_mnist_baseline/metrics.json`
- `reports/training/fashion_mnist_baseline/accuracy_by_class.svg`
- `reports/training/fashion_mnist_baseline/confusion_matrix.svg`

Local Python in this workspace does not include `datasets`, `torch`,
`transformers`, or `sklearn`. Use `uv run` so the script resolves dependencies:

```bash
uv run tools/train_switch_ai_vision.py \
  --dataset zalando-datasets/fashion_mnist \
  --config fashion_mnist \
  --train-split train \
  --eval-split test \
  --max-train-samples 2000 \
  --max-eval-samples 500 \
  --epochs 1 \
  --output-dir models/switchai-fashion-mnist-smoke
```

The output model and metrics are written under `models/`, which is ignored by
git.

## Train Feedback Ranker

Export real Switch It Up session state JSON, then run:

```bash
python3 tools/train_switch_ai_ranker.py \
  --state data/app_state.json \
  --output models/switchai-priors.json
```

If a referenced state path is missing, the command stops and reports the exact
missing file.

## Production Path

1. Train a small Fashion-MNIST classifier to validate the ML pipeline.
2. Train Fashionpedia 4-category detector for garment vs shoe/accessory regions.
3. Train Fashionpedia full detector/attribute model.
4. Add Fashion200K image/text embeddings for style search.
5. Add feedback ranker from real user approvals/rejections.
6. Move heavy training to Hugging Face Jobs or another GPU provider after cost approval.

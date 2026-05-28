# Multi-Dataset SwitchAI Corpus

Date: 2026-05-28

This report expands SwitchAI beyond Fashion-MNIST while keeping data provenance
and storage under control. Raw parquet files are downloaded locally under
`datasets/raw/`, which is ignored by git.

## Local Corpus

- Downloaded files: 13
- Downloaded bytes: 555,971,074
- Approved datasets with local files: 7 registry entries
- Large shards skipped: Fashionpedia train shards and Fashion200K shards above
  the configured 200 MB per-shard cap
- Garments2Look: approved in the registry, but Hugging Face Dataset Viewer
  returned HTTP 500 for parquet discovery, so it was not downloaded by the
  automated script

## Downloaded Dataset Coverage

| Dataset | License | Local files | Local bytes | Use |
| --- | --- | ---: | ---: | --- |
| Fashion-MNIST | MIT | 2 | 36,106,894 | Image classification baseline |
| Fashionpedia 4 Categories | CC-BY-4.0 | 2 | 347,631,009 | Clothing/shoe/bag/accessory detection validation/test |
| Fashionpedia Full | CC-BY-4.0 | 1 | 84,847,838 | Fine-grained detection/segmentation validation |
| Fashion Product Images MIT | MIT | 1 | 86,568,866 | Catalog imagery and visual pretraining |
| Garment Condition Spots | CC-BY-4.0 | 2 | 567,656 | Defect/condition detection |
| Garment Condition Holes | CC-BY-4.0 | 2 | 215,190 | Defect/condition detection |
| Garment Condition Jeans | CC-BY-4.0 | 3 | 33,621 | Denim condition detection |

## Generated Artifacts

- `approved_inventory.json`: live Hugging Face Dataset Viewer inventory for approved datasets
- `download_plan.json`: dry-run capped download plan
- `download_execute.json`: executed capped download report
- `download_product_images_mit.json`: executed download report for the added MIT product-image dataset
- `corpus_report.json`: local file inventory by dataset

## Commands

```bash
python3 tools/dataset_inventory.py --approved-only --write reports/training/multi_dataset/approved_inventory.json
python3 tools/download_training_datasets.py --max-shards 20 --max-shard-bytes 200000000 --max-total-bytes 700000000 --execute --write reports/training/multi_dataset/download_execute.json
python3 tools/download_training_datasets.py --dataset fashion_product_images_mit --max-shards 1 --max-shard-bytes 200000000 --max-total-bytes 200000000 --execute --write reports/training/multi_dataset/download_product_images_mit.json
python3 tools/report_training_corpus.py --write reports/training/multi_dataset/corpus_report.json
```

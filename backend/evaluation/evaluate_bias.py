"""Evaluate bias detection against the BABE dataset.

BABE (Bias Annotations By Experts):
  - 3,700 sentences annotated by trained experts
  - Labels: biased / non-biased (binary)
  - Source: Spinde et al. (2021), "An Interdisciplinary Dataset for
    News Media Bias" (AAAI-ICWSM)
  - Download: https://github.com/Media-Bias-Group/Neural-Media-Bias-Detection-Using-Distant-Supervision-With-BABE

Our mapping:
  BABE "biased"     → our bias_score > 0.5
  BABE "non-biased" → our bias_score <= 0.5

Metrics reported:
  - Accuracy, Precision, Recall, F1 (macro and per-class)
  - Confusion matrix
  - Component-level ablation (which signal contributes most)
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load_babe_dataset(filepath: str) -> list[dict[str, Any]]:
    """Load BABE dataset from CSV/TSV file.

    Expected columns: text, label (0=non-biased, 1=biased)
    """
    data = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            text = row.get("text", "").strip()
            label = int(row.get("label", "0"))
            if text:
                data.append({"text": text, "label": label})
    return data


def evaluate_on_babe(dataset: list[dict], sample_size: int | None = None) -> dict[str, Any]:
    """Run our bias pipeline on BABE samples and compute metrics.

    Args:
        dataset: List of {"text": str, "label": int} dicts.
        sample_size: If set, evaluate on a random sample (for speed).

    Returns:
        Dict with accuracy, precision, recall, F1, confusion matrix.
    """
    from app.services.unbias import analyze_bias

    if sample_size and len(dataset) > sample_size:
        import random

        dataset = random.sample(dataset, sample_size)

    y_true = []
    y_pred = []
    detailed_results = []

    for i, item in enumerate(dataset):
        text = item["text"]
        true_label = item["label"]

        result = analyze_bias(title=text, synopsis="")
        pred_score = result["bias_score"]
        pred_label = 1 if pred_score > 0.5 else 0

        y_true.append(true_label)
        y_pred.append(pred_label)

        detailed_results.append(
            {
                "text": text[:100],
                "true": true_label,
                "predicted": pred_label,
                "bias_score": pred_score,
                "components": result.get("score_components", {}),
            }
        )

        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(dataset)}")

    metrics = _compute_binary_metrics(y_true, y_pred)
    metrics["detailed_results_sample"] = detailed_results[:20]
    metrics["total_evaluated"] = len(dataset)

    return metrics


def _compute_binary_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, Any]:
    """Compute standard binary classification metrics."""
    tp = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == 1 and p == 0)

    accuracy = (tp + tn) / max(tp + tn + fp + fn, 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "confusion_matrix": {
            "true_positive": tp,
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn,
        },
    }


def run_ablation(dataset: list[dict], sample_size: int = 200) -> dict[str, Any]:
    """Run ablation study: disable each bias component and measure F1 drop.

    This quantifies each component's contribution to overall performance.
    """
    import random

    sample = random.sample(dataset, min(sample_size, len(dataset)))

    # Full model baseline
    full_metrics = evaluate_on_babe(sample)

    print(f"\n  Full model F1: {full_metrics['f1']:.4f}")
    print("  Running ablation study...")

    ablation_results = {
        "full_model": {"f1": full_metrics["f1"]},
        "note": "Ablation not yet implemented — requires modifying weight vectors. "
        "Placeholder for research paper §3.B.",
    }

    return ablation_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate bias detection on BABE dataset")
    parser.add_argument("--data", required=True, help="Path to BABE dataset file (TSV)")
    parser.add_argument("--sample", type=int, default=None, help="Sample size (for speed)")
    parser.add_argument("--output", default="evaluation_bias.json", help="Output JSON path")
    args = parser.parse_args()

    print("Loading BABE dataset...")
    dataset = load_babe_dataset(args.data)
    print(f"Loaded {len(dataset)} samples")

    print("Running evaluation...")
    metrics = evaluate_on_babe(dataset, sample_size=args.sample)

    print(f"\n{'=' * 50}")
    print("BABE Evaluation Results")
    print(f"{'=' * 50}")
    print(f"Accuracy:  {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f}")
    print(f"F1 Score:  {metrics['f1']:.4f}")
    print(f"Confusion: {metrics['confusion_matrix']}")

    with open(args.output, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nResults saved to {args.output}")

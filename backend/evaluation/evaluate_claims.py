"""Evaluate check-worthiness detection against CLEF CheckThat! dataset.

CLEF CheckThat! Lab:
  - Task 1: Check-worthiness estimation
  - 50,000+ sentences from political debates and news
  - Labels: check-worthy / not check-worthy (binary)
  - Source: Barron-Cedeño et al. (2020), CLEF-2020/2021/2022 Labs

And evaluate claim verification against LIAR dataset.

LIAR dataset:
  - 12,836 short statements from PolitiFact
  - 6 labels: pants-fire, false, barely-true, half-true, mostly-true, true
  - Source: Wang (2017), "Liar, Liar Pants on Fire" (ACL)
  - Our mapping to 3-class:
      {pants-fire, false}      → REFUTES
      {barely-true, half-true} → NOT_ENOUGH_INFO
      {mostly-true, true}      → SUPPORTS

Metrics:
  - Check-worthiness: MAP@5, Precision@5, nDCG@5
  - Verification: Accuracy, Macro-F1, per-class P/R
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

LIAR_TO_VERDICT = {
    "pants-fire": "REFUTES",
    "false": "REFUTES",
    "barely-true": "NOT_ENOUGH_INFO",
    "half-true": "NOT_ENOUGH_INFO",
    "mostly-true": "SUPPORTS",
    "true": "SUPPORTS",
}


def load_liar_dataset(filepath: str) -> list[dict[str, Any]]:
    """Load LIAR dataset (TSV, no header).

    Columns: id, label, statement, subject, speaker, job, state,
             party, barely_true, false, half_true, mostly_true,
             pants_fire, context
    """
    data = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 3:
                continue
            label = row[1].strip()
            statement = row[2].strip()
            if label in LIAR_TO_VERDICT and statement:
                data.append(
                    {
                        "statement": statement,
                        "original_label": label,
                        "verdict": LIAR_TO_VERDICT[label],
                    }
                )
    return data


def evaluate_checkworthiness_on_clef(
    filepath: str,
    sample_size: int | None = None,
) -> dict[str, Any]:
    """Evaluate check-worthiness detection on CLEF data.

    Expected CSV columns: sentence_id, sentence, label (0/1)
    """
    import asyncio

    from app.services.article_context import build_article_context
    from app.services.claimbuster import get_checkworthy_claims

    data = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get("sentence", "").strip()
            label = int(row.get("label", "0"))
            if text:
                data.append({"text": text, "label": label})

    if sample_size:
        import random

        data = random.sample(data, min(sample_size, len(data)))

    loop = asyncio.new_event_loop()
    y_true = []
    y_scores = []

    for i, item in enumerate(data):
        ctx = build_article_context(item["text"], "")
        claims = loop.run_until_complete(get_checkworthy_claims(ctx.sentences))
        score = claims[0]["score"] if claims else 0.0
        y_true.append(item["label"])
        y_scores.append(score)

        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(data)}")

    loop.close()

    # Compute ranking metrics
    ap_at_5 = _average_precision_at_k(y_true, y_scores, k=5)

    y_pred = [1 if s > 0.5 else 0 for s in y_scores]
    tp = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == 1 and p == 0)

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)

    return {
        "dataset": "CLEF CheckThat!",
        "total_evaluated": len(data),
        "average_precision_at_5": round(ap_at_5, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def evaluate_verification_on_liar(
    dataset: list[dict],
    sample_size: int | None = None,
) -> dict[str, Any]:
    """Evaluate claim verification on LIAR dataset (mapped to 3 classes).

    We use only the statement text (no metadata features) to test our
    NLI pipeline in isolation.
    """
    import asyncio

    from app.services.claimbuster import retrieve_evidence, verify_claim_nli

    if sample_size:
        import random

        dataset = random.sample(dataset, min(sample_size, len(dataset)))

    loop = asyncio.new_event_loop()
    y_true = []
    y_pred = []

    for i, item in enumerate(dataset):
        statement = item["statement"]
        true_verdict = item["verdict"]

        evidence = loop.run_until_complete(retrieve_evidence(statement))
        snippets = [e["snippet"] for e in evidence if e.get("snippet")]
        nli_result = verify_claim_nli(statement, snippets)

        y_true.append(true_verdict)
        y_pred.append(nli_result["verdict"])

        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(dataset)}")

    loop.close()

    labels = ["SUPPORTS", "REFUTES", "NOT_ENOUGH_INFO"]
    metrics = _compute_multiclass_metrics(y_true, y_pred, labels)
    metrics["dataset"] = "LIAR"
    metrics["total_evaluated"] = len(dataset)
    metrics["label_mapping"] = LIAR_TO_VERDICT

    return metrics


def _average_precision_at_k(y_true: list[int], y_scores: list[float], k: int = 5) -> float:
    """Compute average precision at k."""
    paired = sorted(zip(y_scores, y_true, strict=False), reverse=True)
    relevant = 0
    precision_sum = 0.0

    for i, (_, label) in enumerate(paired[:k]):
        if label == 1:
            relevant += 1
            precision_sum += relevant / (i + 1)

    total_relevant = sum(y_true[:k]) if sum(y_true) > 0 else 1
    return precision_sum / min(total_relevant, k) if total_relevant > 0 else 0.0


def _compute_multiclass_metrics(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str],
) -> dict[str, Any]:
    """Compute per-class and macro metrics for multiclass classification."""
    per_class = {}
    f1_scores = []

    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == label and p != label)

        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-8)
        f1_scores.append(f1)

        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(1 for t in y_true if t == label),
        }

    accuracy = sum(1 for t, p in zip(y_true, y_pred, strict=False) if t == p) / max(len(y_true), 1)
    macro_f1 = sum(f1_scores) / len(f1_scores) if f1_scores else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "per_class": per_class,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate claim detection/verification")
    parser.add_argument("--liar", help="Path to LIAR dataset (TSV)")
    parser.add_argument("--clef", help="Path to CLEF CheckThat! dataset (CSV)")
    parser.add_argument("--sample", type=int, default=200, help="Sample size")
    parser.add_argument("--output", default="evaluation_claims.json", help="Output path")
    args = parser.parse_args()

    results = {}

    if args.liar:
        print("Loading LIAR dataset...")
        liar_data = load_liar_dataset(args.liar)
        print(f"Loaded {len(liar_data)} statements")
        print("Evaluating claim verification...")
        results["liar"] = evaluate_verification_on_liar(liar_data, sample_size=args.sample)
        print(f"LIAR Accuracy: {results['liar']['accuracy']:.4f}")
        print(f"LIAR Macro-F1: {results['liar']['macro_f1']:.4f}")

    if args.clef:
        print("\nEvaluating check-worthiness on CLEF...")
        results["clef"] = evaluate_checkworthiness_on_clef(args.clef, sample_size=args.sample)
        print(f"CLEF AP@5: {results['clef']['average_precision_at_5']:.4f}")

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {args.output}")

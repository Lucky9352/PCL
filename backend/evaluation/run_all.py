"""Orchestrate all evaluation benchmarks and produce summary report.

Usage:
  cd backend
  uv run python -m evaluation.run_all --data-dir ./evaluation/datasets/

This script:
  1. Loads all available benchmark datasets from --data-dir
  2. Runs each component evaluation
  3. Produces a unified JSON report + markdown summary table

Expected directory structure:
  datasets/
    babe.tsv           — BABE bias annotations
    liar_train.tsv     — LIAR training set
    liar_test.tsv      — LIAR test set
    clef_checkworthy.csv — CLEF CheckThat! sentences

Datasets are NOT bundled — download instructions in docs/DATASETS.md.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def run_all_evaluations(data_dir: str, sample_size: int = 200) -> dict:
    """Run all available evaluations and produce unified report."""
    data_path = Path(data_dir)
    report: dict = {
        "timestamp": datetime.now(UTC).isoformat(),
        "sample_size": sample_size,
        "evaluations": {},
    }

    # ── Always-on (no HuggingFace / GPU) ──────────
    print("=" * 60)
    print("EVALUATING: Scoring sanity (pure functions)")
    print("=" * 60)
    from evaluation.evaluate_scoring import run_scoring_sanity
    from evaluation.evaluate_tokens import run_synthetic_token_check

    report["evaluations"]["scoring_sanity"] = run_scoring_sanity()
    print(f"  all_passed: {report['evaluations']['scoring_sanity']['all_passed']}")

    print("\n" + "=" * 60)
    print("EVALUATING: Token flagging (synthetic)")
    print("=" * 60)
    report["evaluations"]["tokens_synthetic"] = run_synthetic_token_check()
    print(f"  ok: {report['evaluations']['tokens_synthetic']['ok']}")

    # ── BABE (Bias Detection) ─────────────────────
    babe_file = data_path / "babe.tsv"
    if babe_file.exists():
        print("=" * 60)
        print("EVALUATING: Bias Detection on BABE Dataset")
        print("=" * 60)
        from evaluation.evaluate_bias import evaluate_on_babe, load_babe_dataset

        dataset = load_babe_dataset(str(babe_file))
        metrics = evaluate_on_babe(dataset, sample_size=sample_size)
        report["evaluations"]["bias_babe"] = metrics
        print(f"  F1: {metrics['f1']:.4f}  Accuracy: {metrics['accuracy']:.4f}")
    else:
        print(f"SKIP: BABE dataset not found at {babe_file}")
        report["evaluations"]["bias_babe"] = {"status": "dataset_not_found"}

    # ── LIAR (Claim Verification) ─────────────────
    liar_file = data_path / "liar_test.tsv"
    if not liar_file.exists():
        liar_file = data_path / "liar_train.tsv"
    if liar_file.exists():
        print("\n" + "=" * 60)
        print("EVALUATING: Claim Verification on LIAR Dataset")
        print("=" * 60)
        from evaluation.evaluate_claims import evaluate_verification_on_liar, load_liar_dataset

        dataset = load_liar_dataset(str(liar_file))
        metrics = evaluate_verification_on_liar(dataset, sample_size=sample_size)
        report["evaluations"]["claims_liar"] = metrics
        print(f"  Accuracy: {metrics['accuracy']:.4f}  Macro-F1: {metrics['macro_f1']:.4f}")
    else:
        print(f"SKIP: LIAR dataset not found in {data_path}")
        report["evaluations"]["claims_liar"] = {"status": "dataset_not_found"}

    # ── CLEF CheckThat! (Check-worthiness) ────────
    clef_file = data_path / "clef_checkworthy.csv"
    if clef_file.exists():
        print("\n" + "=" * 60)
        print("EVALUATING: Check-worthiness on CLEF CheckThat!")
        print("=" * 60)
        from evaluation.evaluate_claims import evaluate_checkworthiness_on_clef

        metrics = evaluate_checkworthiness_on_clef(str(clef_file), sample_size=sample_size)
        report["evaluations"]["checkworthiness_clef"] = metrics
        print(f"  AP@5: {metrics['average_precision_at_5']:.4f}  F1: {metrics['f1']:.4f}")
    else:
        print(f"SKIP: CLEF dataset not found at {clef_file}")
        report["evaluations"]["checkworthiness_clef"] = {"status": "dataset_not_found"}

    # ── Summary Table ─────────────────────────────
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"{'Component':<30} {'Metric':<15} {'Score':<10}")
    print("-" * 55)

    for eval_name, eval_data in report["evaluations"].items():
        if eval_data.get("status") == "dataset_not_found":
            print(f"{eval_name:<30} {'—':<15} {'N/A':<10}")
            continue

        if "all_passed" in eval_data:
            print(f"{eval_name:<30} {'pass':<15} {str(eval_data['all_passed']):<10}")
            continue
        if "ok" in eval_data and "flagged_count" in eval_data:
            print(f"{eval_name:<30} {'ok':<15} {str(eval_data['ok']):<10}")
            continue

        if "f1" in eval_data:
            print(f"{eval_name:<30} {'F1':<15} {eval_data['f1']:.4f}")
        if "accuracy" in eval_data:
            print(f"{'':<30} {'Accuracy':<15} {eval_data['accuracy']:.4f}")
        if "macro_f1" in eval_data:
            print(f"{'':<30} {'Macro-F1':<15} {eval_data['macro_f1']:.4f}")
        if "average_precision_at_5" in eval_data:
            print(f"{'':<30} {'AP@5':<15} {eval_data['average_precision_at_5']:.4f}")

    return report


def generate_markdown_report(report: dict) -> str:
    """Generate a markdown table from evaluation results."""
    lines = [
        "# IndiaGround Evaluation Results",
        "",
        f"**Run date:** {report['timestamp']}",
        f"**Sample size per dataset:** {report['sample_size']}",
        "",
        "## Results",
        "",
        "| Component | Dataset | Metric | Score |",
        "|-----------|---------|--------|-------|",
    ]

    for eval_name, eval_data in report.get("evaluations", {}).items():
        if eval_data.get("status") == "dataset_not_found":
            lines.append(f"| {eval_name} | — | — | N/A |")
            continue

        if "all_passed" in eval_data:
            lines.append(f"| {eval_name} | scoring | all_passed | {eval_data['all_passed']} |")
            continue
        if "ok" in eval_data and "flagged_count" in eval_data:
            lines.append(
                f"| {eval_name} | tokens | ok / count | {eval_data['ok']} / {eval_data['flagged_count']} |"
            )
            continue

        dataset = eval_data.get("dataset", eval_name)
        for metric in [
            "accuracy",
            "f1",
            "macro_f1",
            "precision",
            "recall",
            "average_precision_at_5",
        ]:
            if metric in eval_data:
                lines.append(f"| {eval_name} | {dataset} | {metric} | {eval_data[metric]:.4f} |")

    lines.extend(["", "## Per-Class Breakdown", ""])

    for eval_name, eval_data in report.get("evaluations", {}).items():
        per_class = eval_data.get("per_class", {})
        if per_class:
            lines.append(f"### {eval_name}")
            lines.append("")
            lines.append("| Class | Precision | Recall | F1 | Support |")
            lines.append("|-------|-----------|--------|-----|---------|")
            for cls, metrics in per_class.items():
                lines.append(
                    f"| {cls} | {metrics['precision']:.4f} | "
                    f"{metrics['recall']:.4f} | {metrics['f1']:.4f} | "
                    f"{metrics['support']} |"
                )
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run all IndiaGround evaluations")
    parser.add_argument("--data-dir", default="evaluation/datasets", help="Dataset directory")
    parser.add_argument("--sample", type=int, default=200, help="Sample size per dataset")
    parser.add_argument("--output", default="evaluation_report.json", help="JSON output path")
    parser.add_argument("--markdown", default="evaluation_report.md", help="Markdown output path")
    args = parser.parse_args()

    report = run_all_evaluations(args.data_dir, sample_size=args.sample)

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nJSON report saved to {args.output}")

    md_report = generate_markdown_report(report)
    with open(args.markdown, "w") as f:
        f.write(md_report)
    print(f"Markdown report saved to {args.markdown}")

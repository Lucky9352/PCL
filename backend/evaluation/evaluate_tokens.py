"""Token-level bias overlap evaluation (dictionary vs reference spans).

Without the MBIC corpus on disk, runs a **synthetic** check that the
flagging logic returns structured output. With MBIC TSV (columns: text,
tokens or spans), computes rough token F1 against our flagged_tokens.

MBIC-style TSV (optional):
  text<TAB>biased_token1|biased_token2
(one biased span list per line, pipe-separated lowercased tokens)
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _token_f1(predicted: set[str], gold: set[str]) -> dict[str, float]:
    if not gold and not predicted:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not gold:
        return {"precision": 0.0, "recall": 1.0, "f1": 0.0}
    if not predicted:
        return {"precision": 1.0, "recall": 0.0, "f1": 0.0}
    tp = len(predicted & gold)
    prec = tp / len(predicted)
    rec = tp / len(gold)
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4)}


def run_synthetic_token_check() -> dict:
    """Ensure detect_biased_tokens returns list of dicts with expected keys."""
    from app.services.unbias import detect_biased_tokens

    text = "The government slams the opposition for dramatic failure."
    flagged = detect_biased_tokens(text)
    ok = isinstance(flagged, list) and all("word" in x and "suggestion" in x for x in flagged)
    words = {x["word"].strip(".,!?\"'").lower() for x in flagged}
    return {
        "mode": "synthetic",
        "sample_text": text,
        "flagged_count": len(flagged),
        "flagged_sample": flagged[:5],
        "ok": ok and len(words) >= 1,
    }


def evaluate_mbic_style_tsv(path: str) -> dict:
    """Compute mean token F1 over a simple TSV (see module docstring)."""
    from app.services.unbias import detect_biased_tokens

    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) < 2:
                continue
            text, gold_raw = row[0], row[1]
            gold = {t.strip().lower() for t in gold_raw.split("|") if t.strip()}
            flagged = detect_biased_tokens(text)
            pred = {x["word"].strip(".,!?\"'").lower() for x in flagged}
            rows.append(_token_f1(pred, gold))

    if not rows:
        return {"mode": "mbic_tsv", "error": "no rows", "mean_f1": None}

    mean_f1 = sum(r["f1"] for r in rows) / len(rows)
    return {
        "mode": "mbic_tsv",
        "lines": len(rows),
        "mean_f1": round(mean_f1, 4),
        "per_line_sample": rows[:5],
    }


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--tsv", help="Optional MBIC-style TSV for token F1")
    p.add_argument("--output", default="evaluation_tokens.json")
    args = p.parse_args()

    out = evaluate_mbic_style_tsv(args.tsv) if args.tsv else run_synthetic_token_check()
    Path(args.output).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    success = bool(out.get("ok")) if "ok" in out else out.get("mean_f1") is not None
    sys.exit(0 if success else 1)

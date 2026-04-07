#!/usr/bin/env bash
# IndiaGround — one-shot local verification (clean, high-signal output).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  IndiaGround verify_stack"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "▶ Backend: pytest"
(cd backend && uv run pytest tests/ -q)

echo ""
echo "▶ Backend: evaluation (no HuggingFace benchmark downloads)"
(cd backend && uv run python -c "
from evaluation.evaluate_scoring import run_scoring_sanity
from evaluation.evaluate_tokens import run_synthetic_token_check
s = run_scoring_sanity()
t = run_synthetic_token_check()
print('  scoring_sanity: ', 'PASS' if s['all_passed'] else 'FAIL')
print('  tokens_synthetic:', 'PASS' if t['ok'] else 'FAIL')
assert s['all_passed'] and t['ok']
")

echo ""
echo "▶ Backend: ruff"
(cd backend && uv run ruff check app/ evaluation/ tests/ --select E,F,I --ignore E501)

echo ""
echo "▶ Frontend: TypeScript + production build"
(cd frontend && npx tsc --noEmit && pnpm build)

if [[ -n "${DATABASE_URL_SYNC:-}" ]]; then
  echo ""
  echo "▶ Database: alembic upgrade head"
  (cd backend && uv run alembic upgrade head)
else
  echo ""
  echo "◇ Skipping alembic (set DATABASE_URL_SYNC to run migrations against Postgres)."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  All verify_stack checks passed."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

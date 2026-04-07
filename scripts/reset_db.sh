#!/usr/bin/env bash
# ═══════════════════════════════════════════════════
# IndiaGround — Full database reset + clean setup
# ═══════════════════════════════════════════════════
# Usage:  bash scripts/reset_db.sh
#
# What it does:
#   1. Drops ALL tables in the indiaground database
#   2. Clears Alembic migration history
#   3. Runs all Alembic migrations from scratch
#   4. Verifies the schema was created correctly
#   5. Flushes Redis (Celery broker state)
#
# Prerequisites:
#   - PostgreSQL container running (docker compose up -d postgres redis)
#   - uv installed with backend dependencies

set -euo pipefail
cd "$(dirname "$0")/.."

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}════════════════════════════════════════${NC}"
echo -e "${YELLOW}  IndiaGround — Database Reset${NC}"
echo -e "${YELLOW}════════════════════════════════════════${NC}"

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-indiaground}"
DB_PASS="${DB_PASS:-indiaground}"
DB_NAME="${DB_NAME:-indiaground}"
REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"

export PGPASSWORD="$DB_PASS"

echo ""
echo -e "${YELLOW}[1/5] Dropping all tables...${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -q <<'SQL'
DO $$
DECLARE
    r RECORD;
BEGIN
    -- Drop all tables in public schema
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
    -- Drop alembic version tracking
    DROP TABLE IF EXISTS alembic_version CASCADE;
END
$$;
SQL

if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ All tables dropped${NC}"
else
    echo -e "${RED}  ✗ Failed to drop tables${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}[2/5] Verifying empty database...${NC}"
TABLE_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT count(*) FROM pg_tables WHERE schemaname = 'public';" | tr -d ' ')
if [ "$TABLE_COUNT" -eq 0 ]; then
    echo -e "${GREEN}  ✓ Database is clean (0 tables)${NC}"
else
    echo -e "${RED}  ✗ Database still has $TABLE_COUNT tables${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}[3/5] Running Alembic migrations...${NC}"
(cd backend && uv run alembic upgrade head)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}  ✓ Migrations applied successfully${NC}"
else
    echo -e "${RED}  ✗ Migration failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}[4/5] Verifying schema...${NC}"
EXPECTED_TABLES=("articles" "story_clusters" "archived_articles" "analysis_runs" "sources" "alembic_version")
ALL_OK=true
for tbl in "${EXPECTED_TABLES[@]}"; do
    EXISTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
        "SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename='$tbl');" | tr -d ' ')
    if [ "$EXISTS" = "t" ]; then
        COL_COUNT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
            "SELECT count(*) FROM information_schema.columns WHERE table_name='$tbl';" | tr -d ' ')
        echo -e "  ${GREEN}✓${NC} $tbl ($COL_COUNT columns)"
    else
        echo -e "  ${RED}✗${NC} $tbl — MISSING"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = true ]; then
    echo -e "${GREEN}  ✓ All expected tables exist${NC}"
else
    echo -e "${RED}  ✗ Schema verification failed${NC}"
    exit 1
fi

ARTICLE_COLS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c \
    "SELECT count(*) FROM information_schema.columns WHERE table_name='articles';" | tr -d ' ')
if [ "$ARTICLE_COLS" -ge 30 ]; then
    echo -e "  ${GREEN}✓${NC} articles table has $ARTICLE_COLS columns (extended schema confirmed)"
else
    echo -e "  ${YELLOW}⚠${NC} articles table has only $ARTICLE_COLS columns (expected ≥30)"
fi

echo ""
echo -e "${YELLOW}[5/5] Flushing Redis...${NC}"
redis-cli -u "$REDIS_URL" FLUSHALL > /dev/null 2>&1 && \
    echo -e "${GREEN}  ✓ Redis flushed${NC}" || \
    echo -e "${YELLOW}  ⚠ Redis flush skipped (not reachable)${NC}"

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  Database reset complete!${NC}"
echo -e "${GREEN}  Ready for: bash scripts/verify_stack.sh${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"

unset PGPASSWORD

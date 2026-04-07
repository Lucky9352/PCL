#!/bin/bash

# ═══════════════════════════════════════════════════
# IndiaGround — Fresh Start / Hard Reset Script
# ═══════════════════════════════════════════════════
# This script wipes the database, redis, and re-initializes everything.
# WARNING: This DELETEs all scraped articles and analysis results.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Starting Hard Reset of IndiaGround Stack...${NC}"

# 1. Stop Docker Infrastructure and WIPE VOLUMES
echo -e "${YELLOW}📦 Stopping containers and wiping volumes (Database & Redis)...${NC}"
sudo docker compose down -v

# 2. Restart core infrastructure
echo -e "${YELLOW}🛠️  Restarting PostgreSQL and Redis...${NC}"
sudo docker compose up postgres redis -d

# 3. Wait for PostgreSQL to be healthy
echo -e "${YELLOW}⏳ Waiting for PostgreSQL to be ready...${NC}"
until sudo docker compose exec postgres pg_isready -U indiaground -d indiaground > /dev/null 2>&1; do
  sleep 1
done
echo -e "${GREEN}✅ Database is healthy!${NC}"

# 4. Re-apply Database Migrations
echo -e "${YELLOW}📂 Re-applying database migrations...${NC}"
cd backend
uv run alembic upgrade head
cd ..

# 5. Optional cleanup of logs or temp files
rm -rf backend/logs/* 2>/dev/null

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ RESET COMPLETE! Information has been wiped clean.${NC}"
echo -e "${NC}You can now start your services normally:${NC}"
echo -e "${NC}1. pnpm dev:backend${NC}"
echo -e "${NC}2. pnpm dev:worker${NC}"
echo -e "${NC}3. pnpm dev:frontend${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

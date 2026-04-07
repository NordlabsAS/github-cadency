#!/usr/bin/env bash
# Deploy DevPulse. Called by GitHub Actions CI/CD or manually.
# Usage: ./scripts/deploy.sh
#
# Expects:
#   - Working directory is the repo root
#   - .env file exists (or is symlinked from /etc/devpulse/.env)
#   - Docker Compose v2 is installed

set -euo pipefail

COMPOSE="docker compose -f docker-compose.yml"
BACKUP_DIR="/backups"

echo "=== DevPulse Deploy ==="
echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Commit: $(git rev-parse --short HEAD)"

# 1. Pre-deploy backup (skip if DB container isn't running — first deploy)
echo "--- Pre-deploy backup ---"
if docker compose ps --status running --format '{{.Service}}' 2>/dev/null | grep -q '^db$'; then
    ./scripts/backup-db.sh "$BACKUP_DIR"
else
    echo "Database container not running, skipping backup (first deploy?)"
fi

# 2. Build new images with version metadata
echo "--- Building images ---"
DEVPULSE_VERSION=$(cat VERSION 2>/dev/null | tr -d '[:space:]' || echo "0.0.0")
DEVPULSE_BUILD_NUMBER="${DEVPULSE_BUILD_NUMBER:-$(git rev-list --count HEAD 2>/dev/null || echo "0")}"
DEVPULSE_COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
DEVPULSE_DEPLOY_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "Version: $DEVPULSE_VERSION+build.$DEVPULSE_BUILD_NUMBER ($DEVPULSE_COMMIT_SHA)"

export DEVPULSE_VERSION DEVPULSE_BUILD_NUMBER DEVPULSE_COMMIT_SHA DEVPULSE_DEPLOY_TIME
$COMPOSE build

# 3. Ensure database is running and healthy before migrations
echo "--- Starting database ---"
$COMPOSE up -d db
for i in $(seq 1 15); do
    if $COMPOSE exec db pg_isready -U devpulse > /dev/null 2>&1; then
        break
    fi
    if [ "$i" -eq 15 ]; then
        echo "ERROR: Database not ready after 30 seconds"
        exit 1
    fi
    sleep 2
done

# 4. Run database migrations
echo "--- Running database migrations ---"
$COMPOSE run --rm backend alembic upgrade head

# 5. Restart services (recreates only changed containers)
echo "--- Starting services ---"
$COMPOSE up -d

# 6. Wait for backend health check
echo "--- Waiting for backend health check ---"
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "Backend is healthy!"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: Backend health check failed after 60 seconds"
        echo "--- Last 20 backend log lines ---"
        $COMPOSE logs backend --tail 20
        exit 1
    fi
    sleep 2
done

echo "=== Deploy complete ==="

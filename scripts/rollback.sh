#!/usr/bin/env bash
# Rollback to the previous git commit and redeploy.
# Optionally restore a database backup.
#
# Usage:
#   ./scripts/rollback.sh                          # rollback code only
#   ./scripts/rollback.sh --restore-db BACKUP_FILE  # also restore a DB backup
#
# To find available backups: ls -lth /backups/

set -euo pipefail

COMPOSE="docker compose -f docker-compose.yml"
RESTORE_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --restore-db)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --restore-db requires a backup file path"
                echo "Usage: $0 [--restore-db BACKUP_FILE]"
                exit 1
            fi
            RESTORE_FILE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--restore-db BACKUP_FILE]"
            exit 1
            ;;
    esac
done

echo "=== DevPulse Rollback ==="
echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 1. Revert to previous commit
CURRENT=$(git rev-parse --short HEAD)
echo "Current commit: $CURRENT"
git checkout HEAD~1
echo "Rolled back to: $(git rev-parse --short HEAD)"

# 2. Restore DB backup if requested
if [ -n "$RESTORE_FILE" ]; then
    echo "--- Restoring database from $RESTORE_FILE ---"
    if [ ! -f "$RESTORE_FILE" ]; then
        echo "ERROR: Backup file not found: $RESTORE_FILE"
        exit 1
    fi
    gunzip < "$RESTORE_FILE" | docker compose -f docker-compose.yml exec -T db psql -U devpulse devpulse
    echo "Database restored."
fi

# 3. Rebuild and restart
echo "--- Rebuilding and restarting ---"
$COMPOSE build
$COMPOSE up -d

echo ""
echo "=== Rollback complete ==="
echo "You are now on a detached HEAD. To make this permanent:"
echo "  git revert $CURRENT && git push origin main"
echo ""
echo "This will trigger a clean CI/CD deploy of the reverted state."

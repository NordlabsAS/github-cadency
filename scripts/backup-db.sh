#!/usr/bin/env bash
# Backs up the DevPulse PostgreSQL database.
# Usage: ./scripts/backup-db.sh [backup_dir]
#   backup_dir defaults to /backups

set -euo pipefail

BACKUP_DIR="${1:-/backups}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/devpulse-${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Backing up database to ${BACKUP_FILE}..."
docker compose -f docker-compose.yml exec -T db pg_dump -U devpulse devpulse | gzip > "$BACKUP_FILE"
echo "Backup complete: ${BACKUP_FILE} ($(du -h "$BACKUP_FILE" | cut -f1))"

# Retention: delete backups older than 30 days
find "$BACKUP_DIR" -name "devpulse-*.sql.gz" -mtime +30 -delete
echo "Cleaned up backups older than 30 days."

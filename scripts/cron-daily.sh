#!/bin/bash
# Daily digest cron script: research → build → push
# Crontab entry:
#   0 7 * * * /home/dhein/projects/knowledge/scripts/cron-daily.sh >> /home/dhein/projects/knowledge/Meta/cron.log 2>&1

set -e

REPO=/home/dhein/projects/knowledge
LOG=$REPO/Meta/cron.log

cd "$REPO"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Starting daily run" >> "$LOG"

python3 scripts/daily_research.py 2>&1 | tee -a "$LOG"
python3 scripts/build_static.py   2>&1 | tee -a "$LOG"

# Only commit if docs/ has changes (idempotent)
if git diff-index --quiet HEAD -- docs/; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] No docs changes to push" >> "$LOG"
else
    git add docs/
    git commit -m "Daily digest $(date +%Y-%m-%d)"
    git push
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Pushed docs" >> "$LOG"
fi

#!/bin/bash
# Adds a daily 9 AM cron job to fetch Jobright recommendations.
# Run once: bash setup_cron.sh

PYTHON=$(which python3)
SCRIPT="$(cd "$(dirname "$0")" && pwd)/fetch_jobs.py"
LOG="$(cd "$(dirname "$0")" && pwd)/cron.log"
CRON_LINE="0 9 * * * $PYTHON $SCRIPT >> $LOG 2>&1"

# Avoid duplicate entries
(crontab -l 2>/dev/null | grep -v "fetch_jobs.py"; echo "$CRON_LINE") | crontab -
echo "Cron job added: $CRON_LINE"
echo "Logs will write to: $LOG"

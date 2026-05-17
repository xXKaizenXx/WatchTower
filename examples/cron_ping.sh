#!/usr/bin/env sh
# Example: call from cron after your nightly job completes successfully.
# */15 * * * * /path/to/cron_ping.sh

WATCHTOWER_URL="${WATCHTOWER_URL:-http://localhost:8000}"
SERVICE_ID="${SERVICE_ID:?set SERVICE_ID}"
PING_TOKEN="${PING_TOKEN:?set PING_TOKEN}"

curl -sf -X POST "${WATCHTOWER_URL}/ping/${SERVICE_ID}" \
  -H "X-Ping-Token: ${PING_TOKEN}" \
  -H "Content-Type: application/json"

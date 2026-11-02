#!/usr/bin/env bash
# Run on inv-prod-1 by the deploy job.
set -euo pipefail
cd /srv/invoicer
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans

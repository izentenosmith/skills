#!/bin/sh
# Posts a demo invoice to staging. STAGING_URL and STAGING_API_TOKEN come from scripts/.env.
set -eu
. "$(dirname "$0")/.env"
curl -fsS -X POST "$STAGING_URL/invoices" \
  -H "authorization: Bearer $STAGING_API_TOKEN" -H "content-type: application/json" \
  -d '{"id":"demo-1","customer":"ACME","lines":[{"label":"Widgets","cents":1250}]}'

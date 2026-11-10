#!/usr/bin/env bash
# Run by hand on mgr-1: `flash-sale.sh up` before a sale, `flash-sale.sh down` after it.
set -euo pipefail
case "${1:-}" in
  up)
    docker service scale shoplane_api=8 shoplane_worker=4
    docker service update --limit-memory 1G shoplane_api
    ;;
  down)
    docker service scale shoplane_api=3 shoplane_worker=2
    ;;
  *)
    echo "usage: $0 up|down" >&2
    exit 2
    ;;
esac

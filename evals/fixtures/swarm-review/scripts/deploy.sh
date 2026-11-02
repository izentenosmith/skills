#!/usr/bin/env bash
# Run by CI on mgr-1.
set -euo pipefail
cd "$(dirname "$0")/.."
docker stack deploy -c stack.yml shoplane

#!/bin/sh
# Registers this checkout with the build dashboard.
cd "$(dirname "$0")/.." && date -u +%Y-%m-%dT%H:%M:%SZ > .build-registered

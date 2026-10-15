# Changelog

## 2026-10-08
- `recompute_totals`: rewritten as a single batched UPDATE instead of a per-row loop (#212) — 40× faster.

## 2026-09-12
- `recompute_totals`: skip cancelled orders.

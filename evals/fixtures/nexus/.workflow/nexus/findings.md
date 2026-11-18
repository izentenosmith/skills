# Findings that cross slices

## X-1: legacy invoice totals include voided lines
**Found by:** loaders-a, devils-advocate, 2026-11-09 · **Affects:** loaders-a, compare-etl · **Status:** closed
**Evidence:** 1,412 invoices where SUM(lines) ≠ total; all 1,412 have a voided line (`void_flag = 1`).
**Routed:** 2026-11-09 to compare-etl — compare totals with voided lines included.
**Closed by:** PR #209 (loader keeps voided lines, flagged); compare rule updated in compare-etl's brief.

# Issue #87 — timestamps shifted after upgrading to 2.3.0

**Reported by:** the events team at a downstream user, 2026-10-15 09:12 UTC

Since our dependency bot upgraded us to tsfmt 2.3.0 on Tuesday (2026-10-14 ~16:00 UTC), every event our ingestion
service writes has a timestamp **without an offset**, and it's three hours off — our servers run in UTC-3.
We've written about 1.8M events since. Dashboards are wrong and our billing export reads these timestamps.

Pinning to 2.2.1 fixes new events. We don't know how to fix the ones already written.

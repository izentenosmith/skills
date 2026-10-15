# Runbook — checkout

All production operations go through the `ops/` scripts. They act on **production** unless `--env staging` is given.

| Task | Command | Takes effect |
|---|---|---|
| Read logs | `ops/logs --since 30m` | — (read-only) |
| Flip a feature flag | `ops/flags set <flag> on\|off` | within 30 s, no deploy |
| Deploy a version | `ops/deploy <version>` | ~6 min rolling |
| Roll back | `ops/deploy <previous version>` | ~6 min rolling |

Deploy history is in `ops/deploys.log`. Every deploy since v40 has been rollback-safe (additive migrations only).

Incidents: open a tracker item with label `prod-incident`; post-mortems go in `docs/incidents/`.

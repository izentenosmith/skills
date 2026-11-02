# Scoring — Severity, Confidence, the 0–10 Formula, the Gate, Templates

> How a Swarm review is graded and written down. **Rubric version: `v1.0`.** Every output records the
> rubric version and the source version (commit) it read, plus the date of any captured cluster output.
> Each finding names the principle it violates from [`theory.md`](theory.md) (S-n).
>
> The formula is the same one the database, networking, Terraform, pipeline and container-hardening
> skills use, so a 7.4 means the same thing everywhere.

## Severity taxonomy

Severity is set by **what the defect costs on the worst ordinary day**: a node loss, a bad release, a
leaked credential.

| Severity | Meaning | Calibration anchors |
|---|---|---|
| **Critical** | Data loss, a cluster that can't be changed, or a production credential exposed — on an ordinary failure or already | Two managers in production; a single-writer datastore with `replicas: 2+` on local volumes; a primary datastore with no placement constraint; a production secret committed behind `secrets: file:`; the chain "no healthcheck + default update config" on the edge service |
| **High** | A bad release or a node loss hurts much more than it should, or a deploy silently differs from the file | Default `update_config` on a production service; no healthcheck; relying on `depends_on` or `.env`; client-IP logic behind the routing mesh; an internal service published; `:latest` in production; one manager in production; a private registry without `--with-registry-auth` |
| **Medium** | Operability and resilience debt | Managers carrying workloads; no autolock or no backup; no reservations or limits; replicas able to share a node; secrets as environment variables; flat or unencrypted overlays; unbounded restarts; imperative drift; no rollback drill |
| **Low** | Hygiene | Dead ignored keys with no one relying on them; `version:` keys; unnamed networks; rotation documented as "update the secret" |

**Chains.** Record combinations at the severity of their outcome, citing both IDs: no healthcheck +
default update config (a bad release reaches every replica and stops half-way); `replicas: 2` + local
volume + no constraint (two databases, one moving); two managers + no backup (a single failure loses the
control plane with no way back).

## Quality scale (per criterion)

- 🟢 **Well done** · 🟡 **Acceptable / watch** · 🔴 **Not well done**

## Detection confidence

| Tag | Meaning | Counts toward score? |
|---|---|---|
| ✅ **decidable** | Proven by the stack file, deploy script or Dockerfile in the repo, **or by captured or live read-only output** (`docker node ls` showing two managers, `service inspect` showing `FailureAction: pause`) | Yes |
| ⚠️ **proxy** | A static signal approximating the concern: a third-party image documented to have no healthcheck; a backup job named but not shown | Yes, at reduced weight |
| 🔬 **needs-access** | Needs the cluster or the hosts and nothing was supplied: manager count and placement, autolock, cert expiry, firewall rules between nodes, whether the backup restores, node labels | **No.** Flagged, never scored |

**Never run a state-changing command** to raise a confidence level — no deploy, update, scale,
rollback, drain, promote or remove — and never read a secret's value.

## Scoring model

### Evaluation units

| Domain | In-scope objects (the weight) |
|---|---|
| cluster | clusters (usually 1) — **N/A when nothing about the cluster is known: say so and drop it** |
| rollout | services |
| state | services with a volume |
| network | services |
| secrets | services, plus every secret and config declaration |
| scheduling | services |
| stack file | stack files (with the deploy command that reads each) |

### Per-domain score

1. **Grade each criterion proportionally.** `p` = fraction of in-scope objects that satisfy it.
   `p ≥ 0.95` → 🟢 (2 pts) · `0.50 ≤ p < 0.95` → 🟡 (1 pt) · `p < 0.50` → 🔴 (0 pts).
2. **Checklist base.** `base = (Σ points / (2 × criteria)) × 10`.
3. **Severity caps** (lowest wins): any open **Critical** caps at **2.0**; any open **High** caps at **6.0**.
4. **Confidence rule.** Only ✅ and ⚠️ affect the grade; ⚠️ alone may grade a criterion 🟡, never 🔴;
   🔬 never moves the score.

`domain_score = min(base, caps)`, floored at 0, one decimal. The **system score** is the mean of the
domain scores weighted by in-scope objects, caps re-applied. Report uncapped beside capped.

### Bands

| Score | Band |
|---|---|
| 9.0–10 | Exemplary |
| 7.0–8.9 | Good, minor debt |
| 5.0–6.9 | Needs work |
| 3.0–4.9 | Poor |
| 0–2.9 | Critical / unsafe |

### The gate — ready for production

All of these, stated separately:

- the capped score is ≥ 9.0, with no open Critical or High;
- an odd number of managers, 3 or more, for production (S2);
- every service has a healthcheck and an update config that rolls back on failure (S4);
- every stateful service is pinned and single-writer datastores run one replica (S7);
- no secret is committed or passed as an environment variable (S11);
- every image is pinned by digest and the stack file renders with `docker stack config` from the
  deploy's environment (S3, S6);
- the rollback and manager-loss drills have been run, or are scheduled before go-live;
- 🔬 flags number at most 10% of objects.

## Theory → domain mapping

| Domain | Primary principles |
|---|---|
| cluster | Quorum (S2); protect the control plane (S12); overlay ports (S9) |
| rollout | Detect and undo (S4); bound the retries (S5); effective settings (S3) |
| state | State is node-local (S7) |
| network | The mesh (S8); segment and encrypt (S9) |
| secrets | Immutable files (S11) |
| scheduling | Reservations decide placement (S10); immutable references (S6) |
| stack file | Effective settings (S3); desired state (S1) |

## Templates

### Summary — `<repo>/analysis/swarm/summary.md`

```markdown
# <Repo> — Swarm review
> Cluster: <n managers / n workers, or 🔬>. Stacks: <files>. Services: <n>. Source as of <commit>;
> captured output dated <date>; rubric v1.0.

## Fit (Swarm · Compose on a VM · Kubernetes — and why)
## Scores
| cluster | rollout | state | network | secrets | scheduling | stack file | **System** |
|---:|---:|---:|---:|---:|---:|---:|---:|

## Findings
| ID | Object | Anti-pattern | Conf. | Principle | Severity | Evidence |
|----|--------|--------------|-------|-----------|----------|----------|
| SW-STA-01 | stack.yml / postgres | replicas: 2 on a local volume, no constraint | ✅ | State is node-local (S7) | Critical | stack.yml:61 |

## Chains (worst first)
## Severity tally · Needs-access flags
## What is working well
## Gate (each condition, pass/fail, with the reason)
## Drills before go-live
## Handoffs (service security → container-hardening; image healthchecks → dockerfile)
```

Finding IDs: `SW-<CLU|ROL|STA|NET|SEC|SCH|STK>-NN`.

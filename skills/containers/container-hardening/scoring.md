# Scoring — Severity, Confidence, the 0–10 Formula, the Gate, Templates

**Contents:** Severity taxonomy · Quality scale · Detection confidence · Scoring model · Theory → domain mapping · Templates

> How a container hardening review is graded and written down. **Rubric version: `v1.0`.** Every
> output records the rubric version and the source version (commit) it read. Each finding names the
> principle it violates from [`theory.md`](theory.md) (C-n). A finding without a principle is taste.
>
> The formula is the same one the database, networking, Terraform and pipeline skills use, so a 7.4
> means the same thing everywhere.

## Severity taxonomy

Severity is set by **what a compromise of this workload reaches**, which is why a chain can raise a
finding above its row in [`controls.md`](controls.md).

| Severity | Meaning | Calibration anchors |
|---|---|---|
| **Critical** | A compromise of the workload is a compromise of the host, the cluster or a production credential — directly, with no further bug needed | `privileged`; the Docker socket mounted (`:ro` included); `pid: host`; a writable mount of `/`, `/etc` or `/var/lib/kubelet`; `SYS_ADMIN`/`SYS_MODULE`/`DAC_READ_SEARCH` added; a production credential committed or baked into an image; a datastore with a weak or default password published on all interfaces; the daemon API on plain TCP |
| **High** | A compromise is much worse than it needs to be, or a broad exposure exists | Running as root; seccomp or AppArmor disabled; a Kubernetes pod with no seccomp profile facing the internet; host network or IPC; `SYS_PTRACE`/`NET_ADMIN` added; escalation allowed with setuid binaries present; an internal service published on all interfaces; `:latest` in production; fixable Critical CVEs on an internet-facing image; a service account with write permissions mounted by default |
| **Medium** | Defense-in-depth gaps, controlled risk | Default capabilities kept; writable root filesystem; no memory or pids limit; secrets as environment variables; flat network; tag-only image references; no NetworkPolicy; no SBOM or signature verification for third-party images |
| **Low** | Hygiene | Unrotated logs on a single-service host; missing labels; a `HEALTHCHECK` absent with no comment; a safe sysctl undocumented |

**Chains.** When two findings combine into a worse outcome — root + a writable host mount, `SYS_PTRACE` +
`pid: host`, an internet-facing service + no seccomp + a shell in the image — record the chain as its
own line in the summary at the severity of the outcome, citing both finding IDs.

## Quality scale (per criterion)

- 🟢 **Well done**: meets the criterion; matches theory and current practice.
- 🟡 **Acceptable / watch**: works, carries debt.
- 🔴 **Not well done**: violates the criterion.

## Detection confidence

| Tag | Meaning | Counts toward score? |
|---|---|---|
| ✅ **decidable** | Proven by the files in the repo (`privileged: true` at `compose.yaml:14`, an image with no `USER` built from this repo's Dockerfile) **or observed** on a running container (`docker inspect` shows `ReadonlyRootfs=false`) | Yes |
| ⚠️ **proxy** | A static signal that approximates the concern: a third-party image you couldn't inspect that is *documented* to run as root; a volume name shared across trust levels | Yes, at reduced weight (below) |
| 🔬 **needs-access** | Needs the host, the daemon, a node or the cluster: `daemon.json`, the `docker` group, user-namespace remapping, kubelet `SeccompDefault`, whether the CNI enforces NetworkPolicy, what an admission controller enforces, live CVE counts with no scanner available | **No.** Recorded as a flag, never scored |

When the user supplies `docker info`, `daemon.json`, scanner output or `kube-bench` results, findings
from them are ✅. **Never change host, daemon or cluster state, and never print a secret value**, to
raise a confidence level.

## Scoring model

### Evaluation units

| Domain | In-scope objects (the weight) |
|---|---|
| privilege | workloads |
| isolation | workloads |
| kernel | workloads |
| filesystem | workloads |
| resources | workloads |
| network | workloads that publish a port or share a network with one that does |
| secrets | workloads, plus every committed env file and Secret manifest |
| supply chain | distinct images |
| host | hosts or node pools — **N/A without host access; say so and drop it** |

A **workload** is one Compose service, one pod template (Deployment, StatefulSet, DaemonSet, Job,
CronJob), one Swarm service, or one `docker run` invocation. A dev-only Compose stack reviewed only for
laptop safety (see [SKILL.md](SKILL.md)) is scored on privilege, isolation and network only — say so.

### Per-domain score

1. **Grade each criterion proportionally.** `p` = fraction of in-scope objects that satisfy it.
   - `p ≥ 0.95` → 🟢 (2 pts)
   - `0.50 ≤ p < 0.95` → 🟡 (1 pt)
   - `p < 0.50` → 🔴 (0 pts)
2. **Checklist base.** `base = (Σ points / (2 × criteria)) × 10`.
3. **Severity caps** (lowest wins): any open **Critical** caps at **2.0**; any open **High** caps at
   **6.0**.
4. **Confidence rule.** Only ✅ and ⚠️ findings affect the grade. ⚠️ alone may grade a criterion 🟡,
   never 🔴. 🔬 never moves the score.
5. **Accepted risks** (Harden H4) stay open findings for the cap — an accepted Critical still caps at
   2.0 — but are listed separately so the reader sees they were decided, not missed.

`domain_score = min(base, caps)`, floored at 0, one decimal.

### System score

The mean of the domain scores, weighted by in-scope object count, caps re-applied. Report uncapped
beside capped.

### Bands

| Score | Band |
|---|---|
| 9.0–10 | Exemplary |
| 7.0–8.9 | Good, minor debt |
| 5.0–6.9 | Needs work |
| 3.0–4.9 | Poor |
| 0–2.9 | Critical / unsafe |

### The gate

A container estate is **good enough to run as-is** only when all of these hold:

- the capped score is ≥ 9.0;
- no open Critical or High finding remains (accepted risks included — they are listed, not exempt);
- no workload has a host-root interface: privileged, a runtime socket, host PID, or a writable system
  path (C6, C7);
- every workload runs non-root with escalation blocked (C5);
- every production image is pinned by digest and has been scanned (C12);
- no credential is committed or baked into an image (C11);
- 🔬 flags number at most 10% of objects.

State the score-based result and each gate condition separately.

## Theory → domain mapping

| Domain | Primary principles |
|---|---|
| privilege | Least privilege (C4); root is the multiplier (C5) |
| isolation | Host interfaces are root (C6, C7); several fences (C2) |
| kernel | Effective settings (C3); several fences (C2); least privilege (C4) |
| filesystem | Smallest surface (C8); blast radius (C9) |
| resources | Blast radius (C9) |
| network | Expose only what must be reached (C10); blast radius (C9) |
| secrets | Secrets are files at run time (C11); least privilege (C4) |
| supply chain | Know what you ship (C12) |
| host | The shared kernel (C1); host interfaces (C7); runtime observation (C13) |

## Templates

### Per-domain evaluation — `<repo>/analysis/containers/<domain>.md`

```markdown
# <Repo> — <domain> evaluation
> Evaluated against container-hardening/controls.md §<domain> (rubric v1.0).
> Source: <files> — as of <git commit>. Platform: <Compose (production) | Kubernetes | Swarm | docker run>.
> Evidence: <static only | docker inspect on <host> | kubectl on <context>>. Tools run: <trivy config, …>.

## Findings
| ID | Object | Anti-pattern | Conf. | Principle | Severity | Evidence |
|----|--------|--------------|-------|-----------|----------|----------|
| CH-ISO-01 | docker-compose.prod.yml / agent | Docker socket mounted (`:ro` — still the full API) | ✅ | Host interfaces are root (C7) | Critical | docker-compose.prod.yml:41 |

## Needs-access flags (not scored)
## Checklist
| # | Criterion | Satisfied / in scope | p | Result |
|---|-----------|---------------------:|--:|--------|

**Domain score: <0–10>** (base <b>, cap <c> — reason)
```

### Summary — `<repo>/analysis/containers/summary.md`

```markdown
# <Repo> — Container hardening review
> Platform: <…>. Workloads: <n> · images: <n> · hosts: <n or 🔬>. Source as of <commit>; rubric v1.0.

## Threat model (who reaches what; what each workload holds)
## Scores
| privilege | isolation | kernel | filesystem | resources | network | secrets | supply chain | host | **System** |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|

## Severity tally · Needs-access flags
## Chains (worst first, each citing its finding IDs)
## What is working well
## Top findings
## Gate (each condition, pass/fail, with the reason)
## Handoffs (image findings → dockerfile; signing and admission → pipelines)
```

### Harden proof — appended to the summary

```markdown
| Finding | Change | Command | Observed |
|---|---|---|---|
| CH-ISO-01 | socket replaced by a read-only proxy (GET /containers only) | `docker inspect agent --format '{{range .Mounts}}{{.Source}} {{end}}'` | `/srv/agent/config` |
```

Finding IDs: `CH-<PRV|ISO|KRN|FS|RES|NET|SEC|SUP|HST>-NN`.

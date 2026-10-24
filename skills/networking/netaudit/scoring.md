# Scoring — Severity, Confidence, the 0–10 Formula, Templates

> How a network evaluation is graded and written down. **Rubric version: `v1.0`**. Every output
> records the rubric version it was graded against and the source version (commit, export date) it
> read. Each finding must name the principle it violates from [`theory.md`](theory.md) (§N) or
> [`graph-theory.md`](graph-theory.md) (G-N). An evaluation that asserts a defect without naming the
> principle is incomplete.
>
> The formula is the same one the database family uses, so scores mean the same thing across both
> families. The harness (`harness/netreview.py`) applies it in code.

## Severity taxonomy

| Severity | Meaning | Calibration anchors |
|---|---|---|
| **Critical** | Exposure that an outsider can use now, or silent loss of traffic or isolation | SSH/RDP/Telnet/SNMP/SMB reachable from the internet; `allow any → any` into a zone holding data; a management plane reachable from a user or internet zone with no authentication boundary; cleartext secrets with a working default credential |
| **High** | A broad integrity, availability or isolation gap | A single device or link on the path of a critical pair (articulation point or bridge, G4) with connectivity < 2; overlapping CIDRs between reachable networks; a zone with no default-deny; Telnet/HTTP/SNMPv1-v2c management; a routing adjacency without authentication across a trust boundary; an asymmetric path through a stateful firewall |
| **Medium** | Maintainability cost, controlled risk, or debt that will become High as the network grows | An unsummarizable or fragmented address plan; static-route sprawl where a protocol fits; rules with no description or owner; an oversized flat L2 domain; NAT used to paper over overlap; a hub with high betweenness and a shared-fate pair (G6) |
| **Low** | Naming, documentation, cosmetic | Inconsistent naming; missing interface descriptions; unused objects in rule sets |

## Quality scale (per criterion)

- 🟢 **Well done**: meets the criterion; matches theory and current engineering practice.
- 🟡 **Acceptable / watch**: works, but carries operational, security or growth debt.
- 🔴 **Not well done**: violates the criterion. A defect, an anti-pattern, or a theory failure.

## Detection confidence

Not everything can be proven from configuration text. Every anti-pattern carries one of three tags.

| Tag | Meaning | Counts toward score? |
|---|---|---|
| ✅ **decidable** | Provable from the evidence alone: a rule allowing `0.0.0.0/0 → 22`, two overlapping prefixes, a bridge in the recovered graph, `snmp-server community public` | Yes. A confirmed defect. |
| ⚠️ **proxy** | A static signal that approximates a concern and needs judgement: rules without descriptions as a proxy for unowned policy, a degree outlier as a proxy for a hub dependency, any element built on `inferred:` evidence | Yes, at reduced weight (below) |
| 🔬 **needs-data** | Needs runtime state: link utilization, rule hit counts, whether a route is actually installed, whether a device is in use, real failover behaviour, latency | **No.** Recorded as a flag, never scored. |

Graph findings computed by `harness/netgraph.py` inherit the confidence of the evidence they rest on.
A bridge between two configured interfaces is ✅. A bridge through an `inferred:` node is ⚠️.

## Scoring model

### Evaluation units

One evaluation per **domain** per network, each graded with its rubric:

| Domain | Rubric | In-scope objects (the weight) |
|---|---|---|
| addressing | [addressing.md](addressing.md) | `networks[]` entries |
| segmentation | [segmentation.md](segmentation.md) | `flows[]` entries, plus zones |
| routing | [routing.md](routing.md) | routing adjacencies, `route` edges, static routes |
| services | [services.md](services.md) | DNS, DHCP, NAT, LB, gateway, proxy and private-endpoint nodes |
| resilience | [resilience.md](resilience.md) | critical pairs, plus forwarding nodes |
| security | [security.md](security.md) | devices and endpoints with a management or control plane, plus tunnels |

A **network** is the unit the user names: an estate, a site, a subscription, a cluster. Several
networks make an estate.

### Per-domain score

1. **Grade each criterion proportionally.** `p` = fraction of in-scope objects that satisfy it.
   - `p ≥ 0.95` → 🟢 (2 pts)
   - `0.50 ≤ p < 0.95` → 🟡 (1 pt)
   - `p < 0.50` → 🔴 (0 pts)

   "In-scope" excludes objects the criterion cannot apply to. The ports criterion does not apply to
   ICMP flows.
2. **Checklist base.** `base = (Σ points / (2 × criteria)) × 10`.
3. **Severity caps**, applied after the base (lowest wins): any open **Critical** caps at **2.0**;
   any open **High** caps at **6.0**.
4. **Confidence rule.** Only ✅ and ⚠️ findings affect the grade. ⚠️ alone may grade a criterion 🟡,
   never 🔴. 🔬 never moves the score.

`domain_score = min(base, caps)`, floored at 0, one decimal.

### Per-network and estate scores

The **network score** is the mean of its domain scores, weighted by in-scope object count, with the
Critical/High caps re-applied at network level. The **estate score** is the mean of the network
scores, weighted by total objects, with the caps re-applied. Report the uncapped mean beside the
capped one.

### Bands

| Score | Band |
|---|---|
| 9.0–10 | Exemplary |
| 7.0–8.9 | Good, minor debt |
| 5.0–6.9 | Needs work |
| 3.0–4.9 | Poor |
| 0–2.9 | Critical / unsafe |

### The gate

A network is **good enough** — no redesign proposal is owed — only when all of these hold:

- the capped score is ≥ 9.0;
- no open Critical or High finding remains;
- every declared critical pair has node connectivity ≥ 2 (G5). A network with no declared critical
  pairs fails this condition, because its resilience is unassessed;
- 🔬 flags number at most 10% of objects;
- usage is neither `decommissioned` nor `duplicate`.

State the score-based result and each gate condition separately. A 9.2 with a SPOF on the
storefront path is not good enough.

## Triage for large evidence sets

Above **~200 rules or ~50 devices** per network, don't read everything cold:

1. **Signal-scan** all evidence with [`detection-signals.md`](detection-signals.md) and record counts
   per anti-pattern.
2. **Rank** files by signal density. Deep-read the worst 10% or 20 files, whichever is larger, plus a
   random sample of ~10.
3. **State coverage**: "deep-read 24 of 310 rule files; signals cover all 310."

The recovered topology must still cover **every** device and network, because the graph metrics are
only meaningful on the whole graph. Triage limits rule-by-rule reading, not inventory.

## Theory → domain mapping

| Domain | Primary theory to invoke |
|---|---|
| addressing | CIDR and aggregation (§3); NAT and the end-to-end cost (§4); IPv6 (§3) |
| segmentation | Default-deny, least privilege, defense in depth (§11); filtering (§12); broadcast domains (§8) |
| routing | LS/DV behaviour (§5); hierarchy, OSPF, BGP policy (§6); control/data plane separation (§7) |
| services | Middleboxes, DHCP, NAT (§4); DNS and load balancing (§4); delay and throughput (§2) |
| resilience | Cut sets, articulation points, bridges (G4); Menger connectivity (G5); betweenness (G6); percolation (G9); fabric topologies (§9); STP (§8) |
| security | Secure channels (§13); management plane (§14); attacks (§15); authentication (§11) |

## Templates

### Per-domain evaluation — `<network>/analysis/<domain>.md`

```markdown
# <Network> — <Domain> evaluation
> Evaluated against netaudit/<domain>.md (rubric v1.0).
> Source: <evidence paths> — as of <date / git commit>.
> Coverage: <N of M files deep-read; signal-scan covers all M; topology covers all devices>.

## Findings
| ID | Object | Anti-pattern | Conf. | Theory violated | Severity | Evidence |
|----|--------|--------------|-------|-----------------|----------|----------|
| …  | …      | …            | ✅/⚠️/🔬 | Default-deny (§11) | High | infra/nsg.tf:42 |

## Signal counts
| Anti-pattern | Count |
|--------------|------:|

## Needs-data flags (not scored)

## Checklist
| # | Criterion | Satisfied / in scope | p | Result |
|---|-----------|---------------------:|--:|--------|

**Domain score: <0–10>** (base <b>, cap <c> — reason)

## Notes
```

### Per-network summary — `<network>/analysis/summary.md`

```markdown
# <Network> — Network analysis summary
> Usage: in use / barely used / decommissioned / duplicate of <X>. Objects per domain: A/S/R/Sv/Re/Se.
> Source as of <date / commit>; rubric v1.0. Views supported by evidence: physical? logical? policy?

## Scores
| addressing | segmentation | routing | services | resilience | security | **Network** |
|---:|---:|---:|---:|---:|---:|---:|

## Severity tally · Needs-data flags
## Graph summary (computed by the harness)
Components, articulation points, bridges, critical-pair connectivity, top betweenness, robustness
under random vs targeted removal.
## Top findings (worst first)
## Systemic issues
## Overall grade
```

### Estate synthesis — `estate-analysis.md`

```markdown
# Estate-wide network analysis
## Estate score (capped and uncapped)
## Severity heatmap (network × domain)
## Coupling edge list (source network → target network, via, count)
## Shared dependencies (nodes that appear on critical pairs of more than one network)
## Needs-data tally
## Prioritized themes, each tied to its theory
```

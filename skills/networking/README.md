# Networking skills

Five independently usable skills for auditing, designing, diagramming, proposing and blueprinting
computer networks: cloud networks (Terraform, Bicep, ARM, Azure first), on-prem device configs, and
container networking. Each skill folder is complete on its own: its references, plus
`scripts/netgraph.py`, a standard-library Python script that validates `topology.json`, computes the
graph metrics (articulation points, bridges, critical-pair connectivity, betweenness, robustness),
checks addresses and flows, and cross-checks draw.io views against the model. A clone of this repo
also carries an optional coordinator, [`harness/networkflow.py`](../../harness/networkflow.py), that
chains the five; no skill needs it.

```text
Existing network: netaudit → netdesign → netdiagram → netpropose
New network:                 netdesign → netdiagram → netpropose
Accepted proposal:                                      netblueprint
```

| Skill | Purpose |
|---|---|
| [netaudit](netaudit/SKILL.md) | Evidence-based assessment of an existing network. Recovers the topology model (`topology.json`), applies networking theory and a graph-theoretic resilience lens, and reports findings, strengths, weaknesses, improvements and a reproducible 0–10 score. |
| [netdesign](netdesign/SKILL.md) | Designs a new network, or revises an audited one: critical pairs, zones and the flow matrix, a hierarchical addressing plan, routing, services and failure domains. Produces `design.md` and a target `topology.json`. |
| [netdiagram](netdiagram/SKILL.md) | Draws the canonical editable draw.io views: logical topology (L3), segmentation (zones and flows), and physical topology (L1/L2) when on-prem evidence exists. Cell IDs equal model IDs. |
| [netpropose](netpropose/SKILL.md) | Assembles the recommendation: a per-domain decision register, cut-over sequencing from the coupling graph, validation, rollback and blast radius. |
| [netblueprint](netblueprint/SKILL.md) | After explicit acceptance, produces the final topology package: diagrams, `network-design.md` explaining them, and the accepted `topology.json` that a separate IaC skill implements. **No IaC is written here.** |

## Install

All five, from the root of the repo you're working in:

```bash
npx skills add izentenosmith/skills --skill netaudit netdesign netdiagram netpropose netblueprint
```

Or one at a time:

| Skill | Install |
|---|---|
| netaudit | `npx skills add izentenosmith/skills --skill netaudit` |
| netdesign | `npx skills add izentenosmith/skills --skill netdesign` |
| netdiagram | `npx skills add izentenosmith/skills --skill netdiagram` |
| netpropose | `npx skills add izentenosmith/skills --skill netpropose` |
| netblueprint | `npx skills add izentenosmith/skills --skill netblueprint` |

Each installed folder is self-contained, `scripts/netgraph.py` included, because the shared
references are committed as copies in every skill that reads them: an installed skill computes its own metrics with
nothing else on the machine but Python 3. Only the optional coordinator (`harness/networkflow.py`,
`netreview.py`) needs a clone. The repo is public, so no GitHub account is needed; the flags (`-a`, `-g`, `-y`) are in the
[root README](../../README.md#install-with-npx).

## The theory underneath

Two lenses, as relational theory and ER modelling are for the database family:

- **Computer networking** ([theory.md](netaudit/theory.md), §1–§16), from Kurose & Ross,
  *Computer Networking: A Top-Down Approach* (8e) and Tanenbaum & Wetherall, *Computer Networks* (5e).
  It covers layering, delay and throughput, CIDR and aggregation, NAT and middleboxes, routing
  algorithms, OSPF/BGP and policy, SDN, switching/STP/VLANs, data-center fabrics, queues and QoS,
  security principles, firewalls, TLS/IPsec/wireless, management and ICMP, and attacks.
- **Network science** ([graph-theory.md](netaudit/graph-theory.md), G1–G12), from Newman, *Networks*
  (2e) and Barabási, *Network Science* ch. 6. It covers components, articulation points and bridges,
  Menger connectivity and max-flow, betweenness, clustering, degree concentration, percolation under
  random versus targeted failure, and how growth, fitness and decline concentrate hub dependence.

Every finding cites a section from one of the two, and an audit finding without its principle is
incomplete.

## Optional: the coordinated workflow

Nothing in this section is needed to use a skill. It describes what a clone of this repo adds.

Run `python3 harness/networkflow.py --help` for the harness interface. It supports existing-network and
new-network runs, and partial runs when the prerequisite artifacts are available.

**Existing-network runs** go through `netreview.py` first:
1. It redacts every secret from the evidence before a model sees it.
2. It runs one read-only `netaudit` agent per network, which recovers `topology.json`.
3. `netgraph.py` (the same script each skill ships; `harness/netgraph.py` links to it) computes
   articulation points, bridges, critical-pair connectivity, betweenness, robustness curves, CIDR
   overlap and flow exposure **in code**.
4. It scores every domain with the same formula the database family uses.

The **gate** passes a network only when all of these hold:
- the capped score is ≥ 9.0;
- no Critical or High finding is open;
- every declared critical pair has node connectivity ≥ 2 (a network with none declared fails);
- 🔬 flags are at most 10% of objects;
- the network is neither decommissioned nor a duplicate.

The gate and its reasons are recorded. Networks that fail it continue to design, diagrams and proposal.

The harness checks the canonical diagram set, with the checks a skill runs as
`scripts/netgraph.py diagrams`:
- the required files and page names;
- a visible `Network diagram conventions` legend;
- every network labelled with its model CIDR;
- every cell ID a model ID;
- every zone drawn.

The **proposal and the blueprint are separate runs**: the blueprint needs `--proposal-input` and
`--proposal-accepted`. Structural iteration routes through design, diagrams and proposal again, and the
revised proposal needs acceptance before its blueprint is produced.

## Companion references

A shared reference has one canonical file and a committed copy in each skill that reads it, listed in
[`skills/shared.json`](../shared.json). Edit the canonical file, then run
`python3 .github/scripts/sync_shared.py` (or let the pre-commit hook do it); CI fails if a copy drifts.
Copying one skill folder by hand (`cp -r skills/networking/netdesign /target/skills/`) carries
everything it needs.

| Reference | Home / use |
|---|---|
| Theory, graph theory, topology modelling | Canonical in `netaudit/`. Copied into `netdesign/`, `netpropose/`, `netblueprint/` (and topology modelling into `netdiagram/`). The shared principles and the `topology.json` contract. |
| Scoring, audit lenses, domain rubrics, detection signals | `netaudit/`. Audit-only guidance: addressing, segmentation, routing, services, resilience, security. |
| Design patterns | Canonical in `netdesign/`, copied into `netpropose/`. Topology patterns, the addressing method, segmentation, routing, failure domains. |
| Diagram conventions | Canonical in `netdiagram/`, copied into `netpropose/` and `netblueprint/`. The required views, glyphs, IDs and validation. |
| Proposal | `netpropose/`. Decision rules, posture by score band, cut-over sequencing. |
| Blueprint | `netblueprint/`. Package layout, the IaC handoff contract, the `network-design.md` template. |
| `scripts/netgraph.py` | Canonical in `netaudit/scripts/`, copied into each other skill's `scripts/`; `harness/netgraph.py` links to it (the harness isn't installed). Model validation, the graph lens, address and flow checks, the diagram cross-check. |

## Measured

Each skill has one eval in [`evals/`](../../evals/README.md) (evals 16–20): a Terraform/IOS estate to audit that carries a pre-shared key the audit must never echo; requirements whose habitual address plan collides with what's already in use, graded by parsing every CIDR; a target model to draw, graded by parsing the draw.io XML; a proposal hiding an open Critical under a 7.9; and a blueprint request against an unaccepted proposal, graded on what the refusal asks for, not only that it refuses. Reference, do-nothing and plausible-but-wrong controls separate as intended (`python3 evals/controls/make_controls.py --only 16 17 18 19 20`).

**Standalone, measured both ways (n=3 each, against no skill; delta pass rate).** Once with `harness/` staged beside the skills, once with it moved out of the checkout:

| Skill | With harness | Without harness | No skill |
|---|---:|---:|---:|
| netaudit | 1.00 | 1.00 | 0.23 / 0.31 |
| netdesign | 0.90 | 0.90 | 0.30 |
| netdiagram | 0.90 | 0.87 | 0.20 |
| netpropose | 1.00 | 1.00 | 0.70 |
| netblueprint | 1.00 | 1.00 | 0.75 |

No run's report mentions the harness, and the reports that quote metrics quote the skill's own `scripts/netgraph.py`. The misses are the same in both: netdesign's AKS-range assertion and netdiagram's default-deny badges. The badge miss turned out to be the grader's, which read only the zone's label while every run drew the badge as a cell inside the zone.

**Re-run (iteration 23, 2026-11-03, n=3, harness staged):** after the badge assertion was fixed and netpropose made writing `proposal.md` a required step (two of three earlier runs had left it in the reply only), netdiagram, netpropose and netblueprint all score **1.00** on delta and capability, against 0.20, 0.70 and 0.75 for no skill. The benchmark records this run for evals 18–20 and the run without the harness for 16–17.


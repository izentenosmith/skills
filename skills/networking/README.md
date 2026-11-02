# Networking skills

Five independently usable skills for auditing, designing, diagramming, proposing and blueprinting
computer networks: cloud networks (Terraform, Bicep, ARM, Azure first), on-prem device configs, and
container networking. For coordinated work, use [`harness/networkflow.py`](../../harness/networkflow.py).
The harness lives in `harness/` and calls the skills here.

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

The installer dereferences the companion-reference symlinks, so each installed folder is
self-contained. It installs the skills only: `harness/networkflow.py`, `netreview.py` and
`netgraph.py` need a clone. Flags (`-a`, `-g`, `-y`) are in the
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

## Coordinated workflow

Run `python3 harness/networkflow.py --help` for the harness interface. It supports existing-network and
new-network runs, and partial runs when the prerequisite artifacts are available.

**Existing-network runs** go through `netreview.py` first:
1. It redacts every secret from the evidence before a model sees it.
2. It runs one read-only `netaudit` agent per network, which recovers `topology.json`.
3. `netgraph.py` computes articulation points, bridges, critical-pair connectivity, betweenness,
   robustness curves, CIDR overlap and flow exposure **in code**.
4. It scores every domain with the same formula the database family uses.

The **gate** passes a network only when all of these hold:
- the capped score is ≥ 9.0;
- no Critical or High finding is open;
- every declared critical pair has node connectivity ≥ 2 (a network with none declared fails);
- 🔬 flags are at most 10% of objects;
- the network is neither decommissioned nor a duplicate.

The gate and its reasons are recorded. Networks that fail it continue to design, diagrams and proposal.

The harness checks the canonical diagram set:
- the required files and page names;
- a visible `Network diagram conventions` legend;
- every network labelled with its model CIDR;
- every cell ID a model ID;
- every zone drawn.

The **proposal and the blueprint are separate runs**: the blueprint needs `--proposal-input` and
`--proposal-accepted`. Structural iteration routes through design, diagrams and proposal again, and the
revised proposal needs acceptance before its blueprint is produced.

## Companion references

Shared references use relative symlinks to one canonical copy. When installing a single skill folder
outside this repository, dereference the links during copy (for example,
`cp -RL skills/networking/netdesign /target/skills/`).

| Reference | Home / use |
|---|---|
| Theory, graph theory, topology modelling | Canonical in `netaudit/`. Linked from `netdesign/`, `netpropose/`, `netblueprint/` (and topology modelling from `netdiagram/`). The shared principles and the `topology.json` contract. |
| Scoring, audit lenses, domain rubrics, detection signals | `netaudit/`. Audit-only guidance: addressing, segmentation, routing, services, resilience, security. |
| Design patterns | Canonical in `netdesign/`, linked from `netpropose/`. Topology patterns, the addressing method, segmentation, routing, failure domains. |
| Diagram conventions | Canonical in `netdiagram/`, linked from `netpropose/` and `netblueprint/`. The required views, glyphs, IDs and validation. |
| Proposal | `netpropose/`. Decision rules, posture by score band, cut-over sequencing. |
| Blueprint | `netblueprint/`. Package layout, the IaC handoff contract, the `network-design.md` template. |

## Measured

Each skill has one eval in [`evals/`](../../evals/README.md) (evals 16–20): a Terraform/IOS estate to audit that carries a pre-shared key the audit must never echo; requirements whose habitual address plan collides with what's already in use, graded by parsing every CIDR; a target model to draw, graded by parsing the draw.io XML; a proposal hiding an open Critical under a 7.9; and a blueprint request against an unaccepted proposal. Reference, do-nothing and plausible-but-wrong controls separate as intended (`python3 evals/controls/make_controls.py --only 16 17 18 19 20`). **First runs (n=1), against no skill:** netaudit 1.00 vs 0.23, netdesign 0.90 vs 0.30, netdiagram 0.90 vs 0.20, netpropose 0.90 vs 0.70, netblueprint 1.00 vs 1.00 — its eval checks a refusal a bare agent also makes.

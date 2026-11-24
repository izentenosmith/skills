---
name: netaudit
description: Audits an existing computer network — cloud network IaC (Terraform, Bicep, ARM), router/switch/firewall configs, Kubernetes or compose networking, IP plans — recovering its topology and reporting strengths, weaknesses, evidence-backed findings and a repeatable 0–10 score. Use when assessing network quality, exposure, resilience or single points of failure, or before planning a redesign. It evaluates only; netdesign and netpropose handle changes, and it never writes IaC.
---

# 🔎 netaudit

Give a balanced assessment: what is working well, what is deficient, and what could improve. A score
of 9.0 or more is the score threshold for "good". Do not call a network good when the gate finds an
open Critical/High finding, a critical pair with connectivity below 2, decommissioned/duplicate
status, or too many unresolved needs-data flags. State the score-based result and those conditions
separately.

## When NOT to use

- Designing a new network or the redesign of this one → `netdesign`.
- Only drawing the topology → `netdiagram`.
- Turning findings into a decision and cut-over plan → `netpropose`.
- Locking down the hosts and cloud accounts beyond the network → `hardening`.
- Reviewing the Terraform code itself — state, modules, change safety → `terraform`.

## Where this fits

This skill evaluates and stops. For a redesign, continue with [netdesign](../netdesign/SKILL.md), then
[netdiagram](../netdiagram/SKILL.md) and [netpropose](../netpropose/SKILL.md). Each runs on its
own, and so does this one: everything it computes, it computes with the script in its own folder or by
hand.

The audit **does not prescribe**. It does not draw a target topology, write IaC, or decide what to
retire. An audit that also prescribes has an incentive to shape its findings toward the prescription.
It produces evidence, theory, a recovered model and a number. The decisions belong to the next skill.

Scope is **static evidence**: configuration text, IaC, policies, exports and inventories. Anything that
needs a live network — utilization, latency, rule hit counts, installed routes, failover behaviour,
whether a device is still in use — is a 🔬 *needs-data* flag and is never graded as fact. **Never
connect to a device, controller or cloud API** unless the user explicitly asks you to, and then only
for read-only exports.

Reference docs, all in this folder:

- [theory.md](theory.md) — the networking principles every finding cites (§1–§16): layering, delay
  and throughput, addressing, NAT, routing, SDN, switching, fabrics, security, management
- [graph-theory.md](graph-theory.md) — the network-science lens (G1–G12): components, articulation
  points and bridges, Menger connectivity, betweenness, degree distributions, percolation and
  resilience, network growth
- [topology-modeling.md](topology-modeling.md) — the `topology.json` contract, modelling rules, the
  reverse-engineering procedure (M3) and drills
- [scoring.md](scoring.md) — severity, confidence tags, the 0–10 formula, the gate, triage, templates
- [audit-lenses.md](audit-lenses.md) — cross-cutting lenses: dead/duplicate networks, drift,
  dark space, coupling, secrets in evidence
- [addressing.md](addressing.md) · [segmentation.md](segmentation.md) · [routing.md](routing.md) ·
  [services.md](services.md) · [resilience.md](resilience.md) · [security.md](security.md) — the
  per-domain rubrics: 🟢 well done, 🔴 anti-patterns, checklist
- [detection-signals.md](detection-signals.md) — the grep/regex behind each anti-pattern, with its
  confidence tag and a vendor/platform translation table
- `scripts/netgraph.py` — validates `topology.json` and computes the graph lens, the address checks and
  the flow checks from it. Python 3 standard library only; it reads the one file you name and writes
  nothing.

---

## 📐 Calibrate the pass

Pick one up front and say which:

| Mode | Input | Run |
|---|---|---|
| **Domain audit** | One domain of one network (e.g. only the NSGs) | Steps 0–2 for that domain |
| **Network audit** | One network's evidence | Steps 0–3 |
| **Estate audit** | Several networks (sites, subscriptions, clusters) | Steps 0–4 |
| **Model audit** | A topology diagram or design document, no configs | Grade it against [topology-modeling.md](topology-modeling.md) and the rubrics' checklists. Report gaps with severity. Skip the formula, which needs evidence counts. |

Also state the **evidence platforms**, inferred from syntax: `azurerm_*` → Terraform/Azure;
`Microsoft.Network/*` → Bicep/ARM; `interface GigabitEthernet` → IOS; `set security policies` →
Junos; `config firewall policy` → FortiOS; `kind: NetworkPolicy` → Kubernetes. The signals are
written for Terraform/Azure and IOS. [detection-signals.md](detection-signals.md) says how each one
translates.

---

## 🧭 Step 0: Inventory

- [ ] **Locate the evidence**: IaC folders, config exports, policy manifests, IPAM exports, existing
  diagrams. If none exists, ask for it.
- [ ] **Redact secrets before reading further.** Device configs and IaC carry passwords, type-7
  keys, SNMP communities and pre-shared keys. Never copy a secret value into an output. Record the
  *kind* of secret and where it is (`fw-a.conf:212, SNMPv2c community, default value`). The Security
  signals in [detection-signals.md](detection-signals.md) find them; quote the line number, not the
  line.
- [ ] **Count objects per domain** (networks, flows/rules, routing adjacencies and routes, service
  nodes, critical pairs, managed devices). The counts weight the scores.
- [ ] **Usage status** per network: in use / barely used / decommissioned / duplicate. This is usually
  not in the evidence, so ask or mark 🔬. A **duplicate** (one environment copying another's address
  space and policy) is decidable by comparison.
- [ ] **Critical pairs**: ask which reachabilities *are* the service. If the user is not available,
  infer them from the evidence (published listeners, default routes, database subnets) and label them
  `inferred:`.
- [ ] **Source version**: the commit or export date every evaluation will cite.
- [ ] **Output location**: the repo's convention if it has one; otherwise
  `<network>/analysis/<domain>.md`, `<network>/analysis/summary.md`,
  `<network>/analysis/topology.json` and `estate-analysis.md`. Never write results inside this
  skill's folder.

## 🗺️ Step 1: Recover the topology

Follow [topology-modeling.md](topology-modeling.md) M3. Write `topology.json`, with `file:line`
evidence for every element and `inferred:` for every modelling inference. Reconcile it with its
checklist.

Then compute the graph lens ([graph-theory.md](graph-theory.md)): components, articulation points,
bridges, node/edge connectivity for each critical pair, betweenness, and robustness under random vs
targeted removal. **Compute them; don't eyeball them.** Run the script in this skill's folder:

```bash
python3 <this skill's folder>/scripts/netgraph.py analyze <network>/analysis/topology.json
```

Exit 1 means `topology.json` breaks the contract: fix what it lists and run it again. Exit 0 prints a
Markdown report (`--json` for the raw numbers): the metrics, a per-pair table with each minimum cut,
the robustness table, and ✅/⚠️ findings with IDs (`NG-SPOF-…`, `NG-OVERLAP-…`, `NG-MGMT-…`). Its findings
join yours. Keep the IDs, check each against its evidence, and paste the report into the summary's
graph section. Without a Python interpreter, work the graph by hand with the procedures in
graph-theory.md G4–G9: list each critical pair's cut set, and say that the robustness curve was not
computed. If the repo carries this family's optional harness, `harness/netreview.py` can run the
whole audit as a pipeline and calls this same script, so its numbers match yours; nothing here needs
it.

## 🔬 Step 2: Evaluate each domain

One domain, one rubric, one evaluation file. For each:

- [ ] **Triage if large** (scoring.md): signal-scan with [detection-signals.md](detection-signals.md),
  deep-read the worst files, and **state coverage**.
- [ ] **Walk the rubric's 🔴 anti-patterns** against every in-scope object.
- [ ] **Every finding carries five things**: object, anti-pattern, **confidence** (✅ / ⚠️ / 🔬),
  **the theory it violates** (a § or G section), **severity** per [scoring.md](scoring.md), and
  **evidence** as `file:line`. A finding missing any of them is incomplete. The theory matters most:
  a defect without the principle it breaks is taste.
- [ ] **Cross-domain criteria** need both inputs. A route table that sends traffic through a firewall
  (routing) whose rules allow it (segmentation). A peering (routing) between overlapping networks
  (addressing). Record each finding in the domain where the defect lives.
- [ ] **Count per criterion** how many in-scope objects satisfy it. The score is computed from these
  counts, not estimated.

Write `<network>/analysis/<domain>.md` from the template in [scoring.md](scoring.md).

## 🧮 Step 3: Score and summarize each network

Apply the formula in [scoring.md](scoring.md): `p` per criterion, base, caps, confidence rule. **Show
the arithmetic**. Two auditors with the same findings must land on the same number. Then write
`summary.md`: scores per domain, the network score, the severity tally, the **🔬 flag tally**, the
graph summary, top findings, systemic issues, and the gate conditions one by one.

## 🌐 Step 4: Synthesize the estate

With more than one network, write `estate-analysis.md`: capped and uncapped estate scores; a severity
heatmap (network × domain); **the coupling edge list** (source network → target network, via, count:
peerings, VPNs, shared firewalls, shared DNS); shared dependencies (nodes on the critical pairs of
several networks — the estate-level SPOFs); the 🔬 tally; and prioritized themes, each tied to its
theory. netpropose derives sequencing from the coupling list, so give it counts, not adjectives.

---

## 🛑 Stopping rule

Stop when all of these hold:

- [ ] `topology.json` exists, covers every device and network in the evidence, and every element has
  evidence or an `inferred:` reason.
- [ ] Every domain in scope has an evaluation with its **coverage stated**.
- [ ] Every finding has confidence, theory, severity and evidence.
- [ ] Every score shows `p`, base and cap, and follows the formula.
- [ ] Every 🔬 flag is listed by name: none dropped, none scored.
- [ ] Summaries and the synthesis exist for the mode chosen.

Then stop. Past full checklist coverage, an extra Low in a domain already capped by a Critical is
noise that buries the Critical. Don't start designing: hand off.

---

## Subagents — optional

Worth it on an estate; rarely on one network.

**Fan out Steps 1–2**: one read-only delegate per network (or per domain when one network's rule set
is huge), dispatched together and collected before Step 3. Keep **scoring, the graph metrics and the
synthesis** in the main thread. The formula only produces comparable numbers when one auditor applies
it, and coupling only shows when every network is seen at once.

**Dispatch contract.** A delegate starts with no history. Give it:
- the **prior**: what the estate is, which networks are decommissioned or duplicates;
- the **target**: exactly which evidence it owns;
- the **context it cannot infer**: paste the relevant rubric, its signals and the `topology.json`
  schema inline, with the severity and confidence definitions and the rubric version;
- the **return shape**: findings table, per-criterion counts, signal counts, coverage, 🔬 flags, its
  slice of `topology.json`, and "not evaluated" per domain, so a silent delegate is distinguishable
  from a clean one;
- an explicit *"report conclusions, not file excerpts, and never copy a secret value."*

Delegates **never score** and never write outside their own evaluation files.

---

## Rules of Engagement

1. **Static scope, honestly labelled.** A runtime claim is a 🔬 flag, never a defect.
2. **No finding without its theory.** Name the principle — default-deny (§11), aggregation (§3),
  Menger connectivity (G5) — or drop the finding.
3. **Evidence is a line reference.** "Several NSGs are permissive" is a count. A finding names the
   rule and the line.
4. **Score by formula, not by feel.** Show the arithmetic. Graph metrics come from the graph, not
   from intuition about the diagram.
5. **Evaluate, don't prescribe.** A fix hint is fine ("restrict the source to the bastion subnet").
   A target topology is netdesign's job.
6. **Read-only, and no secrets.** Never alter a device, a config, a policy or a cloud resource. Never
   reproduce a credential.
7. **Record the rubric version** (`v1.0`) and the source version in every output.

## Handoff

> Audited `<N>` objects across `<K>` networks (rubric v1.0, source `<commit/date>`). Estate score
> `<x.x>` — `<band>`, capped by `<finding>`. `<c>` Critical · `<h>` High · `<m>` Medium · `<l>` Low;
> `<k>` 🔬 flags open. Critical pairs below connectivity 2: `<list>`. Outputs: `<paths>`.

For a full recommendation, hand this audit and its `topology.json` to
**[netdesign](../netdesign/SKILL.md)**, then **[netdiagram](../netdiagram/SKILL.md)** and
**[netpropose](../netpropose/SKILL.md)**. State the score, the capping finding, the gate conditions
and the open-flag count: they decide whether the network passes the gate and what the next stage needs
to know.

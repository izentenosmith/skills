# Contoso — Network proposal (contoso-prod redesign)

> **Status: Proposed** — circulated 2026-10-23 for review at the network change board on 2026-10-29.
> Sources: audit `../audit/` is not included in this workspace (rubric v1.0, git 9c41e0d); design
> `../design/design.md` rev 3; diagrams `../diagrams/`. Platform: Azure, West Europe.

## 1. Recommendation

Keep routing and services; contain the Bastion SSH exposure immediately; rework addressing (renumber
analytics) and resilience (active-active VPN). Expected: network score 2.0 → 9.1, every gate condition
met except lan-onprem → snet-analytics, which stays at κ=1 until the DC team adds a second endpoint.

## 2. Decision register

| Domain | Score | Decision | Findings |
|---|---:|---|---|
| segmentation | 2.0 | Refactor — remove `allow-ssh-any` in the first window | NET-SEG-01 |
| addressing | 6.0 | Rework — renumber vnet-analytics to 10.3.0.0/16 | NET-ADR-01 |
| resilience | 6.0 | Rework — VPN gateway active-active, two tunnels | NET-RES-01 |
| routing | 9.2 | Keep | — |
| services | 9.0 | Keep | — |
| security | 8.8 | Refactor — rule descriptions and owners | NET-SEC-03 |
| legacy-batch | — | Retire after usage is confirmed (flow logs for 14 days) | NET-LEN-01 |

## 3. Target

`design/topology.json` (meta.stage design, rev 3) and `diagrams/logical-topology.drawio`,
`diagrams/segmentation.drawio`. They match: same IDs, CIDRs and flows.

## 4. Cut-over

| # | Step | Findings | Validation | Rollback | Blast radius |
|---|---|---|---|---|---|
| 1 | Delete `allow-ssh-any`; Bastion from on-prem only | NET-SEG-01 | SSH from internet refused; admins reach Bastion from on-prem | re-add the rule | mgmt only |
| 2 | VPN gateway to VpnGw2AZ active-active; second tunnel | NET-RES-01 | both tunnels up; export succeeds on either | revert SKU change window | lan-onprem ↔ analytics during resize |
| 3 | Build vnet-analytics-v2 10.3.0.0/16 alongside; migrate workers; DC team updates 4 firewall objects | NET-ADR-01 | BI export succeeds from 10.3.1.0/24 two nights running | route BI back to the old VNet | analytics, BI export |
| 4 | Retire vnet-legacy-batch after 14 days of empty flow logs | NET-LEN-01 | no flows for 14 days | re-peer | none expected |

## 5. Open questions

1. Second on-prem VPN endpoint (DC team).
2. Usage of vnet-legacy-batch.

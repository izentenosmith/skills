# contoso-prod — Network analysis summary
> Usage: in use. Objects per domain: addressing 12 · segmentation 13 · routing 6 · services 5 · resilience 3 · security 4.
> Source as of git 9c41e0d / 2026-10-14; rubric v1.0. Views supported by evidence: logical, policy (no physical — cloud only).

## Scores
| addressing | segmentation | routing | services | resilience | security | **Network** |
|---:|---:|---:|---:|---:|---:|---:|
| 6.0 (base 8.3, High cap) | 2.0 (base 9.4, Critical cap) | 9.2 | 9.0 | 6.0 (base 6.7, High cap) | 8.8 | **2.0** capped · 7.9 uncapped |

## Severity tally
Critical 1 · High 3 · Medium 4 · Low 5

## Needs-data flags (not scored)
- 🔬 NET-LEN-01: `vnet-legacy-batch` (10.9.0.0/16, peered to the hub) — the owner says it has been unused since
  2024; no flow logs or VM inventory in the evidence. Usage recorded as **barely used / unconfirmed**.
- 🔬 Actual failover behaviour of the on-prem VPN endpoint.
- 🔬 NSG rule hit counts.

## Graph summary (netgraph)
1 component. Articulation points on critical pairs: vgw-hub, onprem-dc. Bridges: e-vpn-onprem-1, e-onprem-lan.
internet → snet-web κ=2 · snet-app → snet-data κ=2 · lan-onprem → snet-analytics κ=1 (cut {vgw-hub}).

## Top findings (worst first)
| ID | Object | Finding | Conf. | Theory | Severity | Evidence |
|---|---|---|---|---|---|---|
| NET-SEG-01 | nsg-bastion rule `allow-ssh-any` | SSH (22/tcp) allowed from `Internet` into the Bastion subnet; no earlier deny | ✅ | §11, §14 | Critical | infra/hub.tf:121 |
| NET-ADR-01 | vnet-analytics | 10.20.0.0/16 equals the on-prem DC range reachable over the VPN | ✅ | §3 | High | infra/analytics.tf:3, infra/hub.tf:66 |
| NET-RES-01 | vgw-hub | single VPN gateway (VpnGw1, active-active off) is an articulation point on lan-onprem → snet-analytics | ✅ | G4, G5 | High | infra/hub.tf:58 |
| NET-RES-02 | onprem-dc | single on-prem endpoint (inferred) | ⚠️ | G4 | High | inferred |

## Coupling (estate view)
| Source | Target | Via | Count |
|---|---|---|---|
| lan-onprem (BI, nightly 02:00 UTC) | vnet-analytics | VPN + hub routing | 1 scheduled export |
| on-prem firewall rules | vnet-analytics | static objects for 10.20.0.0/16 | 4 rules (per DC team, 🔬) |

## Gate
- Score 2.0 < 9.0 — **not met**
- Open Critical/High — **not met** (1 Critical, 3 High)
- Every critical pair κ ≥ 2 — **not met** (lan-onprem → snet-analytics κ=1)
- 🔬 ratio 3/43 = 7% ≤ 10% — met
- Usage not decommissioned/duplicate — met

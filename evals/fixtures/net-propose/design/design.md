# Contoso — Network design (redesign of contoso-prod)

> Stage: design · status: proposed · rev 3, 2026-10-22. Model: `topology.json` (same folder).
> Input audit: `../audit/` (rubric v1.0, source git 9c41e0d / 2026-10-14).

## 1. Scope, requirements and assumptions

- One Azure region (West Europe), one hub, two workload spokes (storefront `vnet-prod`, `vnet-analytics`),
  hybrid connectivity to the Amsterdam data centre over IPsec.
- Availability: storefront 99.9%; the nightly BI export (on-prem → analytics, 02:00 UTC) must not miss
  two consecutive nights.
- Assumption: the on-prem VPN endpoint is a single device owned by the DC team and out of scope here.

## 2. Critical pairs

| Pair | Why |
|---|---|
| internet → snet-web | customer traffic to the storefront |
| snet-app → snet-data | every order write |
| lan-onprem → snet-analytics | nightly BI export to finance |

## 3. Zones and flow matrix

| Zone | Trust | Members | Default |
|---|---:|---|---|
| internet | 0 | — | — |
| edge | 1 | snet-web | deny in (NSG DenyAllInBound) |
| onprem | 2 | lan-onprem | deny in (on-prem firewall, out of scope) |
| transit | 2 | snet-fw, snet-gw | deny in |
| app | 2 | snet-app, snet-analytics | deny in |
| data | 3 | snet-data | deny in |
| mgmt | 3 | snet-bastion | deny in |

| From → To | Proto/ports | Reason | Flow ID |
|---|---|---|---|
| internet → edge | tcp/443 | storefront HTTPS | fl-internet-edge-443 |
| edge → app | tcp/8443 | web to app API | fl-edge-app-8443 |
| app → data | tcp/5432 | app to PostgreSQL | fl-app-data-5432 |
| mgmt → app | tcp/22 | Bastion SSH | fl-mgmt-app-22 |
| onprem → mgmt | tcp/443 | admins reach Bastion | fl-onprem-mgmt-443 |
| onprem → app | tcp/443 | BI pulls analytics exports | fl-onprem-app-443 |

Bastion is reachable from on-prem only. No internet → mgmt flow exists in the target.

## 4. Addressing plan

| Network | CIDR | Parent | Purpose |
|---|---|---|---|
| vnet-hub | 10.0.0.0/16 | — | hub |
| snet-fw | 10.0.1.0/26 | vnet-hub | AzureFirewallSubnet |
| snet-gw | 10.0.2.0/27 | vnet-hub | GatewaySubnet |
| snet-bastion | 10.0.3.0/26 | vnet-hub | AzureBastionSubnet |
| vnet-prod | 10.1.0.0/16 | — | storefront production |
| snet-web / snet-app / snet-data | 10.1.1.0/24 · 10.1.2.0/24 · 10.1.3.0/24 | vnet-prod | tiers |
| vnet-analytics | **10.3.0.0/16** (was 10.20.0.0/16) | — | analytics |
| snet-analytics | **10.3.1.0/24** (was 10.20.1.0/24) | vnet-analytics | analytics workers |
| lan-onprem | 10.20.0.0/16 | — | Amsterdam DC (excluded from Azure allocation) |

`vnet-legacy-batch` (10.9.0.0/16) is not carried into the target model.

## 5. Topology and routing

Hub-and-spoke. Spokes peer to the hub with `use_remote_gateways`; spoke subnets route `0.0.0.0/0` to
`afw-hub`. No spoke-to-spoke peering.

## 6. Services and resilience

- `afw-hub`: Azure Firewall Premium, zones 1–3.
- `vgw-hub`: VPN gateway VpnGw2AZ, **active-active**, two tunnels (`e-vpn-onprem-1`, `e-vpn-onprem-2`).
- `agw-web`: Application Gateway WAF v2, zones 1–3.

## 7. Graph results (netgraph, target model)

internet → snet-web κ=2; snet-app → snet-data κ=2; lan-onprem → snet-analytics κ=1, cut set
{onprem-dc} — the on-prem endpoint (inferred, out of scope); see open question 1.

## 8. Audit traceability

| Change | Audit finding |
|---|---|
| Remove the internet → mgmt SSH rule; Bastion from on-prem only | NET-SEG-01 |
| Renumber vnet-analytics 10.20.0.0/16 → 10.3.0.0/16 | NET-ADR-01 |
| VPN gateway active-active (second tunnel) | NET-RES-01 |
| Drop vnet-legacy-batch from the model | NET-LEN-01 |

## 9. Open questions

1. Can the DC team provide a second on-prem VPN endpoint? Until then lan-onprem → snet-analytics stays at κ=1.
2. Is vnet-legacy-batch still used? The owner believes not; there are no flow logs in the evidence.

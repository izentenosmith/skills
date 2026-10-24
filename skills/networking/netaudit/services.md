# Services — DNS, DHCP, NAT, Load Balancing, Gateways, Endpoints

> Criteria for grading the network services that sit in the path: DNS resolvers and zones, DHCP,
> NAT and egress gateways, load balancers and ingress controllers, proxies, VPN/ExpressRoute
> gateways, and private endpoints (`nodes[]` of those kinds). Theory is in [`theory.md`](theory.md)
> §2, §4, §7. Severity follows [`scoring.md`](scoring.md).

## 🟢 Well done

- **DNS is redundant and split where it must be.** At least two resolvers per site or VNet.
  Private zones linked to every network that needs them. Private endpoint names resolve to private
  addresses everywhere they are used. Conditional forwarding between on-prem and cloud is explicit.
- **DHCP has redundancy** (failover pair or split scope), with relays configured on every routed
  segment that needs it. On-prem, snooping is enabled on access switches.
- **Egress NAT is deliberate.** A known, stable set of public egress addresses (a NAT gateway or
  firewall SNAT), sized for port exhaustion, rather than per-VM public IPs.
- **Load balancers have health probes** that test the application, not just the port. Backends span
  failure domains. Session persistence is a stated choice.
- **PaaS reached privately.** Private endpoints or service endpoints for data services, with public
  network access disabled where the private path exists.
- **Gateways are sized and redundant**: active/active VPN, zone-redundant SKUs, two circuits for
  ExpressRoute or Direct Connect.

## 🔴 Not well done

### Single DNS resolver or forwarder
**What:** One resolver, one forwarder VM or one conditional forwarder on the path of every lookup.
**Why:** Nothing works when name resolution fails, so it is an articulation point for every critical
pair (G4), even if it is not drawn on the data path.
**Detect:** count resolvers configured per network (`dns_servers`, `ip name-server`). ✅.
**Severity:** High.

### PaaS reachable publicly when a private path exists
**What:** A storage account, database or key vault with a private endpoint that still allows public
network access, or with no network restriction at all.
**Why:** It bypasses the network boundary entirely. Policy on the private path protects nothing
(§11).
**Detect:** `public_network_access_enabled = true`, missing `network_rules`/`network_acls`. ✅.
**Severity:** High for data services; Medium otherwise.

### Private DNS not linked where private endpoints are used
**What:** A private endpoint whose `privatelink.*` zone is not linked to a consuming network, or
on-prem resolvers that don't forward the zone.
**Why:** Clients resolve the public address, then either fail or silently take the public path.
**Detect:** zone links vs consuming networks. ✅.
**Severity:** Medium; High when the fallback is a public path.

### Per-host public IPs instead of controlled egress
**What:** VMs or nodes with their own public IPs for outbound traffic.
**Why:** Every host is directly exposed and directly egressing, so egress filtering and stable allow
listing are impossible (§4, §11).
**Detect:** `public_ip_address_id` on NICs; `associate_public_ip_address`. ✅.
**Severity:** Medium; High when the NIC's NSG is permissive.

### Load balancer without meaningful health probes
**What:** No probe, a TCP probe on a port that answers even when the app is down, or backends in one
zone only.
**Why:** Traffic goes to dead backends, or to a single failure domain.
**Detect:** the probe definition, and backend placement. ✅ for configuration; real health is 🔬.
**Severity:** Medium.

### Gateway or NAT as an undeclared single point of failure
**What:** A non-redundant VPN gateway SKU, a single circuit, one NVA doing all NAT, or a NAT gateway
in one zone serving zone-redundant workloads.
**Why:** It is the articulation point on every on-prem or egress path (G4).
**Detect:** SKU and zone fields; one gateway node on the critical pair. ✅.
**Severity:** High when it sits on a critical pair.

### SNAT port exhaustion risk
**What:** Many backends sharing one public IP for outbound connections at scale.
**Why:** Each public IP has a finite set of source ports. Exhausted ports cause intermittent outbound
failures (§4).
**Detect:** the ratio of backends to egress IPs. ⚠️ proxy; actual exhaustion is 🔬.
**Severity:** Medium.

## Checklist

Criteria graded across in-scope service nodes:

1. Redundant across failure domains (or stated as accepted risk).
2. Reached privately where a private path exists; public access disabled.
3. Name resolution works for every consuming network (zone links, forwarders).
4. Health-checked in a way that tests the service (LBs, gateways).
5. Egress goes through a controlled, stable set of addresses.
6. Sized for its load (SKU, SNAT ports, throughput). Configuration ⚠️, load 🔬.

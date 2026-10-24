# Segmentation — Zones, Filtering and Flows

> Criteria for grading who may talk to whom: `zones[]` and `flows[]` in `topology.json`, built from
> NSGs/security groups, firewall policies, ACLs, zone-based firewalls and Kubernetes NetworkPolicies.
> Theory is in [`theory.md`](theory.md) §8, §11–§12. Severity follows [`scoring.md`](scoring.md).
> The harness checks any-any rules, internet-to-management exposure and missing default-deny in code.

## 🟢 Well done

- **Zones by trust and function.** Internet, DMZ/edge, application tiers, data, management, and
  partners each get their own zone, with a documented trust level. Every forwarding node is in exactly
  one zone.
- **Default-deny between zones**, explicit or platform-implicit and cited. Every allowed flow is a
  stated exception (§11).
- **Least privilege per flow.** A specific source (a zone, an application security group, a service
  tag), a specific destination, and specific protocol and ports. Each flow has a description, owner or
  ticket.
- **Stateful filtering at trust boundaries** (§12). Return traffic is allowed by state, not by a mirror
  rule that opens high ports inbound.
- **East-west control.** Workloads in the same environment do not reach each other by default.
  Microsegmentation (ASGs, NetworkPolicies) where tiers share a subnet.
- **Egress is filtered**, not only ingress: workloads reach the internet through a proxy, firewall or
  NAT with an allow-list.
- **The management plane is its own zone**, reachable only from a bastion or jump zone.

## 🔴 Not well done

### Management ports reachable from the internet
**What:** An allow flow from `internet`, `*`, `0.0.0.0/0` or `Internet` service tag to 22, 23, 3389,
161/162, 445, 5985/5986, or a device's web management port.
**Why:** It exposes the management plane to everyone (§11, §14). These ports are scanned
continuously, and credential attacks against them are routine (§15).
**Detect:** flow scan, accounting for higher-priority denies. ✅.
**Severity:** Critical.

### Any-any allow
**What:** An allow rule with any source, any destination and any port, or a NetworkPolicy that allows
everything.
**Why:** It erases the boundary the zone was meant to create (§11).
**Detect:** flow scan. ✅.
**Severity:** Critical into a zone with trust ≥ 2 that holds data; High otherwise.

### No default-deny for a zone
**What:** A zone with allow flows but no explicit or cited implicit deny. That includes a Kubernetes
namespace with no NetworkPolicy, and an AWS security group with `0.0.0.0/0` egress plus a broad
ingress.
**Why:** Without a deny, everything not mentioned is allowed, and the allow rules document nothing
(§11). One compromised workload reaches the whole zone.
**Detect:** per zone, look for a lowest-precedence deny or a cited platform default. ✅.
**Severity:** High.

### Overly broad sources or port ranges
**What:** Sources such as `10.0.0.0/8` or `VirtualNetwork` where one subnet is meant. Port ranges such
as `1-65535` or `1024-65535` inbound.
**Why:** The rule allows far more than the flow it was written for (§11, least privilege).
**Detect:** source prefix length and port span. ⚠️ proxy (the intended flow is a judgement).
**Severity:** Medium; High into the data or management zone.

### Shadowed and redundant rules
**What:** Rules that can never match, because a higher-priority rule already decides every packet
they cover. Duplicate rules.
**Why:** Dead policy misleads reviewers. A shadowed *deny* is a control that looks present and isn't.
**Detect:** order-aware rule analysis. ✅ when the platform's evaluation order is known.
**Severity:** Medium when a deny is shadowed; Low otherwise.

### Flat L2 across trust levels
**What:** Different trust levels sharing one VLAN, subnet or bridge. Inter-VLAN routing with no filter.
Trunks that carry every VLAN everywhere.
**Why:** L2 adjacency bypasses L3 filtering. ARP spoofing and MAC flooding work inside the domain
(§8, §15).
**Detect:** zone assignment per L2 domain; `switchport trunk allowed vlan all`. ✅.
**Severity:** High.

### No egress control
**What:** Workloads in trusted zones with unrestricted outbound internet access.
**Why:** Exfiltration and command-and-control need outbound access. Egress filtering is the
defense-in-depth layer that contains a compromise (§11).
**Detect:** allow flows from trust ≥ 2 zones to `internet` with `*` ports. ✅.
**Severity:** Medium; High for the data zone.

### Unowned rules
**What:** Rules with no description, owner or ticket reference.
**Why:** Nobody can tell whether a rule is still needed, so rule sets only grow.
**Detect:** missing `description`/`remark`/`comment`. ⚠️ proxy.
**Severity:** Low.

## Checklist

Criteria graded across in-scope `flows[]` (zone-level criteria count zones):

1. Does not expose management ports to untrusted zones.
2. Is not an any-any allow.
3. The destination zone has a default-deny (graded per zone).
4. Source, destination and ports are as narrow as the stated flow requires.
5. Is reachable in evaluation order (not shadowed), and not a duplicate.
6. Crosses a trust boundary only through stateful filtering.
7. Has a description, owner or ticket.
8. Egress from trusted zones is filtered (graded per zone).

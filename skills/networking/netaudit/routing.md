# Routing — How Packets Find Their Way

> Criteria for grading the control plane: routing adjacencies (`l3-adjacency` edges with
> `attrs.protocol`), steering routes (`route` edges), and static routes. Sources are OSPF/BGP/IS-IS
> configuration, static routes, cloud route tables (UDRs), peering and gateway settings, and transit
> gateways. Theory is in [`theory.md`](theory.md) §5–§7. Severity follows [`scoring.md`](scoring.md).

## 🟢 Well done

- **A dynamic protocol where topology changes**, statics only at stub edges. Each choice is explained.
- **Hierarchy.** OSPF areas with a clean backbone, summaries at area borders, BGP at administrative
  boundaries (§6). Routing tables stay short because addressing summarizes (§3).
- **Explicit policy at every external boundary.** BGP prefix filters in both directions, max-prefix
  limits, no default route accepted from or sent to a peer unintentionally, and no transit for traffic
  the organisation should not carry (§6).
- **Authenticated adjacencies** across any boundary where an attacker could inject routes (§6, §13).
- **Symmetric paths through stateful devices.** Forward and return traffic traverse the same firewall,
  or the design states how state is synchronized (§12).
- **Cloud route tables are deliberate.** Every UDR has a purpose. `0.0.0.0/0` to an NVA is matched by
  the NVA's capacity and redundancy. Gateway route propagation is enabled or disabled on purpose.
- **Convergence and failure behaviour are designed**: timers and BFD where failover speed matters
  (actual speed is 🔬).

## 🔴 Not well done

### Asymmetric routing through a stateful firewall
**What:** The forward path crosses firewall A and the return path crosses firewall B, or bypasses
filtering entirely. A typical cloud cause: the UDR on one subnet points to an NVA, while the peer
subnet has no matching UDR.
**Why:** Stateful filters drop the half of the flow they did not see (§12). Bypass paths defeat the
policy.
**Detect:** compare route tables on both sides of each critical pair. ✅ when both tables are in the
evidence.
**Severity:** High.

### Blackholes and loops
**What:** A route whose next hop is not reachable, a `None`/`Null0` next hop over a range that is in
use, or two static routes pointing at each other.
**Why:** Traffic is dropped silently, or loops until its TTL expires (§5).
**Detect:** next-hop resolution over `topology.json`. ✅.
**Severity:** High on a critical pair; Medium elsewhere.

### Unfiltered external BGP
**What:** eBGP sessions with no inbound or outbound prefix filter, or no max-prefix limit.
**Why:** It accepts or leaks any route. Route leaks and hijacks propagate through exactly these
sessions (§6).
**Detect:** `neighbor … remote-as` without a `prefix-list`/`route-map`/`maximum-prefix`. ✅.
**Severity:** High.

### Unauthenticated routing adjacencies across a trust boundary
**What:** OSPF/BGP/EIGRP neighbours on shared or untrusted segments without authentication or GTSM.
**Why:** Anyone on the segment can form an adjacency and inject routes (§6, §15).
**Detect:** protocol stanzas without `authentication`/`password`/`ttl-security`. ✅.
**Severity:** High on a shared or external segment; Low on a dedicated point-to-point link.

### Static-route sprawl
**What:** Many static routes maintaining reachability that a protocol would learn. Statics duplicated
across devices.
**Why:** Statics don't converge. Every topology change needs manual edits on several devices, and
stale statics become blackholes (§5).
**Detect:** count statics per device, relative to adjacencies. ⚠️ proxy.
**Severity:** Medium.

### No summarization at boundaries
**What:** Area borders or BGP edges that advertise every specific prefix.
**Why:** Larger tables, more churn, and instability that spreads across the boundary (§6).
**Detect:** no `area … range` / `aggregate-address` where the plan allows one. ⚠️.
**Severity:** Low–Medium.

### Unintended transitivity or missing transit
**What:** Spokes that are expected to reach each other with no transit configured (peering is not
transitive). Or the opposite: `allow_gateway_transit`/forwarded traffic enabled where isolation was
the intent.
**Why:** The real reachability graph differs from the one people believe in (topology-modeling M2.3).
**Detect:** peering flags vs stated intent. ✅ for the flags; ⚠️ for the intent.
**Severity:** High when isolation is violated; Medium when reachability is merely missing.

## Checklist

Criteria graded across in-scope adjacencies and routes:

1. Has a reachable next hop and forms no loop.
2. External sessions filter prefixes in both directions and limit them.
3. Adjacencies across shared or external segments are authenticated.
4. Paths through stateful devices are symmetric (graded per critical pair).
5. Uses a dynamic protocol, or the static is justified at a stub.
6. Summarized at the boundary where the plan allows.
7. Peering and transit flags match the stated isolation or reachability intent.

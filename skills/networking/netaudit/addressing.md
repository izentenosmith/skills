# Addressing — The IP Plan

> Criteria for grading a network's address plan: `networks[]` in `topology.json`, built from VNet and
> subnet declarations, interface addresses and IPAM exports. Theory is in [`theory.md`](theory.md)
> §3–§4. Severity follows [`scoring.md`](scoring.md). Signals and confidence tags are in
> [`detection-signals.md`](detection-signals.md). The harness checks overlap, containment and
> duplicates in code (`harness/netgraph.py`).

## 🟢 Well done

- **One allocation hierarchy.** Region or site → environment → tier. Each level is a contiguous,
  aligned block that summarizes into one prefix at the level above, so routing tables stay short (§3).
- **No overlap among networks that are, or will be, connected.** That includes on-prem ranges that
  reach the cloud over VPN or ExpressRoute.
- **Sized to purpose with a stated growth reserve.** Subnets are sized for their workload plus
  headroom. Cloud-reserved addresses (Azure keeps 5 per subnet) are accounted for. Unallocated
  reserve is documented as reserve.
- **Private space used for private networks.** RFC 1918 for internal networks, RFC 6598 only where
  carrier-grade NAT requires it, public space only where it is actually owned and announced.
- **IPv6 planned**, even if not deployed: a /48 or /56 per site, a /64 per subnet, no NAT66.
- **One source of truth.** The IPAM, or IaC, is authoritative and matches the configs.

## 🔴 Not well done

### Overlapping CIDRs between reachable networks
**What:** Two networks with intersecting prefixes, connected through peering, VPN, transit or routing.
**Why:** Longest-prefix match (§3) can deliver a packet to only one of them. The other becomes
unreachable from the shared path, or traffic is blackholed. It is the address-plan defect hardest to
fix later, because the fix is renumbering.
**Detect:** prefix intersection over `networks[]`, restricted to graph-reachable pairs. ✅ decidable.
**Severity:** High. Medium when the networks are not reachable today (a latent collision for any
future peering).

### Subnet outside its parent
**What:** A subnet whose prefix is not inside the VNet/VPC or site block it belongs to.
**Why:** It breaks the hierarchy that aggregation depends on (§3). On most clouds it is a deployment
error. On-prem it means routes the summary does not cover.
**Detect:** containment check against `parent`. ✅.
**Severity:** High when the subnet is routed, Medium otherwise.

### Unsummarizable, fragmented plan
**What:** One environment's subnets scattered across non-contiguous blocks; sites that don't
align on bit boundaries.
**Why:** Every fragment is a route in every table that carries it. Summaries become impossible, and
policy written by prefix needs one rule per fragment (§3, §6).
**Detect:** the minimal set of covering prefixes per environment is larger than 1–2. ⚠️ proxy.
**Severity:** Medium.

### Public range used internally
**What:** Non-RFC1918 space on internal networks that the organisation does not own, typically a
"made-up" `1.1.1.0/24` or `100.64/10` used without CGNAT.
**Why:** It shadows real internet destinations, so users cannot reach the legitimate owner of the
range (§3).
**Detect:** classification of each prefix. ✅ for the range; ownership is 🔬.
**Severity:** Medium; High when the range is a well-known public service.

### Oversized flat subnets
**What:** /16-sized subnets or VLANs holding thousands of hosts in one broadcast domain.
**Why:** Broadcast and ARP load grow with the domain (§8). The blast radius of an L2 failure or
attack is the whole subnet. Policy cannot distinguish tiers inside it.
**Detect:** prefix length per subnet against purpose. ⚠️ proxy (actual host count is 🔬).
**Severity:** Medium.

### Undersized subnets with no reserve
**What:** Subnets at or near capacity, with no free adjacent space to grow into.
**Why:** Growth then forces a second, non-contiguous subnet, which brings fragmentation.
**Detect:** prefix length vs declared or counted hosts. 🔬 when host counts are not in the evidence.
**Severity:** Low–Medium.

### NAT used to hide overlap
**What:** Overlapping networks joined through NAT instead of renumbered.
**Why:** NAT breaks end-to-end addressing (§4). It complicates logging and troubleshooting, and it
doubles the state on the translating device. Acceptable as a stated, temporary migration measure.
**Detect:** NAT rules whose inside and outside both translate private overlapping ranges. ✅.
**Severity:** Medium.

### Plan and evidence disagree
**What:** IPAM entries with no config, and configured prefixes missing from the IPAM (audit-lenses §2).
**Why:** It is a single-source-of-truth failure. The next allocation will collide.
**Detect:** set difference. ✅ when both are in the evidence.
**Severity:** Medium.

## Checklist

Criteria graded across in-scope `networks[]` (the counts feed the formula):

1. No overlap with any reachable network.
2. Contained in its declared parent.
3. Part of a summarizable block for its environment or site.
4. Address class fits its use (private internally; public only where owned).
5. Sized to purpose (not flat-oversized, not exhausted), with reserve documented.
6. Present and consistent in the source of truth (IPAM/IaC ↔ configs).
7. IPv6 allocation planned or explicitly out of scope.

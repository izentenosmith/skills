# Theory Foundations — Computer Networking

> The networking principles behind the audit rubrics, the design patterns and the proposals built on
> them. Every theoretical term a finding, a verdict or a design decision cites is defined **here once**
> (§1–§16) and only referenced elsewhere. The graph-theoretic lens is in
> [`graph-theory.md`](graph-theory.md) (G1–G12). The shared model is in
> [`topology-modeling.md`](topology-modeling.md).
>
> Sources are cited by section: **K&R** = Kurose & Ross, *Computer Networking: A Top-Down Approach*,
> 8th ed.; **T&W** = Tanenbaum & Wetherall, *Computer Networks*, 5th ed. Everything is paraphrased.
> Facts neither book states are marked **[beyond texts]** with the standard to cite instead.
> Both books' cryptographic examples (3DES, MD5/SHA-1 HMAC, RSA key transport) illustrate *mechanism*.
> They are not recommended settings; §13 states current practice.

## §1. Layering, encapsulation and the end-to-end argument

A network stack is a set of layers. Each layer offers a **service** to the layer above through an
**interface**, and implements it with a **protocol** private to that layer (T&W §1.4). The Internet
uses five layers:

| Layer | Unit | Examples |
|---|---|---|
| Application | message | HTTP, DNS, SMTP |
| Transport | segment | TCP, UDP |
| Network | datagram | IP, plus the routing protocols |
| Link | frame | Ethernet, 802.11 |
| Physical | bits | |

Each layer **encapsulates** what it gets from above by prepending its own header. Devices implement
only the layers they need: hosts implement all five, routers L1–L3, switches L1–L2 (K&R §1.5). Each
layer has its own addressing (names, IP addresses, MAC addresses), which keeps the layers
independent.

The **IP hourglass** has one universal network protocol, carried over many link layers, under many
applications. The **end-to-end argument** (Saltzer, Reed & Clark, 1984) follows from it: a function
that can be completed correctly only with knowledge held at the endpoints belongs at the endpoints.
An in-network version of it is at most a performance optimization (K&R §4.5 sidebar; RFC 1958).
Reliable delivery is the canonical example. So are confidentiality and integrity to the real peer.

**Audit lens**
- A control placed at a layer that cannot see the property it claims to enforce gives partial
  protection at best. An L3/L4 rule cannot enforce "only GET /health". An L2 switch cannot enforce IP
  policy. "Port 443" does not mean HTTPS.
- In-network mechanisms (link encryption, a TLS-terminating proxy, carrier MPLS separation) do not
  give endpoint guarantees (§13).
- Every encapsulation (VXLAN, GRE, IPsec, IPv6-in-IPv4) adds header bytes and lowers the effective
  MTU. Without MTU/MSS adjustment, large packets blackhole (§14).

## §2. Packet switching: delay, loss and throughput

Packet switching shares link capacity on demand (statistical multiplexing). It gives no guarantee of
delivery, order, delay or bandwidth: the network layer is **best effort** (K&R §1.3, §4.1).

- **Nodal delay:** `d_nodal = d_proc + d_queue + d_trans + d_prop`, where `d_trans = L/R` (packet
  bits over link rate) and `d_prop = d/s` (distance over ~2–3×10⁸ m/s). Transmission depends on
  packet size and rate, not distance. Propagation depends on distance, not size (K&R §1.4.1).
- **Traffic intensity** `La/R` (L bits per packet, a packets/s). Above 1 the queue grows without
  bound. As it approaches 1, average queuing delay rises steeply. Buffers are finite, so overload
  becomes loss (K&R §1.4.2).
- **Throughput** of a path is the minimum of its link rates, or of a shared link's fair share `R/n`
  when n flows cross it (K&R §1.4.4).
- **Store-and-forward** over N links: `N·L/R` of transmission delay end to end.

**Audit lens**
- A latency objective below the propagation floor for the distance cannot be met. Synchronous
  cross-region replication is the usual case.
- A throughput objective above the narrowest element on the path (VPN gateway SKU, NAT gateway,
  firewall throughput, instance NIC, peering link) cannot be met.
- Capacity sized to averages with no burst headroom runs near `La/R → 1` at peak. Real utilization is
  always 🔬 needs-data.

## §3. Addressing: CIDR, aggregation, longest-prefix match, IPv6

Addresses belong to **interfaces**, not hosts. A **subnet** is the set of interfaces reachable
without crossing a router. **CIDR** writes a prefix as `a.b.c.d/x`: the top x bits name the network
and the rest identify interfaces. Blocks are powers of two and must be **aligned** on their own size
(K&R §4.3.2; T&W §5.6.2).

- **Hierarchy and aggregation.** Routers know their own region in detail and other regions only as
  summaries. One aggregate stands for many networks, so tables grow with the number of *regions*, not
  hosts. T&W's example: 720 routers need 720 entries flat, 53 with two levels, 25 with three. The cost
  is slightly longer paths, because a summary may not be optimal (T&W §5.2.6). Scattered or misaligned
  allocations cannot be summarized.
- **Longest-prefix match.** When several prefixes match, the most specific wins. If none matches, the
  default route applies. Lookup runs in hardware (TCAM) at line rate (K&R §4.2.1). A more-specific
  route therefore *silently overrides* an aggregate: legitimately when a customer moves providers,
  dangerously when a stray /24 or /32 steers traffic around a firewall.
- **Private space** (RFC 1918): `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`. Shared CGNAT space
  is `100.64.0.0/10` (RFC 6598) **[beyond texts]**. Private ranges must never appear on the public
  internet.
- **Allocation chain:** ICANN → RIRs (ARIN, RIPE, APNIC, LACNIC, AFRINIC) → ISPs → organizations.
- **IPv6** uses 128-bit addresses and a fixed 40-byte header with no checksum and no router
  fragmentation. Options move to chained extension headers, and anycast is native. Transition is by
  tunneling (IPv6 in IPv4, protocol 41) or dual stack (RFC 4213 **[beyond texts]**). Changing the
  network layer is slow (K&R §4.3.4).

**Audit lens**
- Two overlapping prefixes on networks that can reach each other: longest-prefix match can deliver to
  only one of them. The fix is renumbering, which is why overlap is the costliest addressing defect.
- An allow rule written with an aggregate (`10.0.0.0/8`) covers far more than its intended members, so
  it breaks least privilege (§11).
- IPv6 enabled (SLAAC/router advertisements on) but absent from the filters is an unfiltered parallel
  network.

## §4. NAT, DHCP, load balancers and other middleboxes

A **middlebox** is any on-path device that does more than standard IP forwarding (RFC 3234): NAT;
security functions (firewall, IDS); performance functions (cache, load balancer). Middleboxes widen
the IP narrow waist, and they break the rule that the core looks only at IP headers (K&R §4.5).

- **NAT** shows one public address outside and rewrites source address and port on the way out. A
  translation table maps replies back. The 16-bit port field gives roughly 60k concurrent mappings per
  public address. NAT has architectural costs:
  - Ports end up addressing hosts.
  - An L3 device rewrites L4 fields.
  - Inbound connections fail until an outbound packet creates state, so end-to-end reachability is
    lost.
  - A NAT crash kills every flow through it.
  - Protocols that embed addresses (FTP, SIP, H.323) break.

  NAT blocks unsolicited inbound traffic only *as a side effect*. **NAT is not a firewall** (K&R
  §4.3.3; T&W §5.6.2).
- **DHCP** assigns address, mask, gateway and DNS server in four steps: Discover → Offer → Request →
  ACK, on UDP 67/68. It needs a relay where no server is on the subnet. Leases expire (K&R §4.3.2).
  DHCP is unauthenticated, so a rogue server can hand out a malicious gateway or resolver.
  Snooping is the mitigation **[beyond texts]**.
- **Load balancers** act as layer-4 switches. They pick a backend by destination address and port,
  and rewrite the public VIP to the backend address. This hides internal structure and keeps clients
  off the backends (K&R §6.6.1).
- **Internet presence** needs three independent pieces (K&R §5.4.6): connectivity with a prefix, BGP
  announcement of that prefix, and authoritative DNS with glue in the TLD. Any one missing means the
  service is unreachable.

**Audit lens**
- Every on-path middlebox without redundancy is an articulation point (G4). So is every resolver or
  DHCP server on the path.
- Treating NAT as the security boundary, with no explicit inbound deny, is a segmentation finding.
- Many backends behind one egress address risk **SNAT port exhaustion**.
- Backends reachable directly (public IPs, or rules open to `0.0.0.0/0` on backend ports) defeat the
  load balancer's isolation.

## §5. Forwarding, routing and routing algorithms

**Forwarding** is the local, nanosecond-scale data-plane act of moving a packet from input to output
port. **Routing** is the network-wide control-plane computation that fills the forwarding tables (K&R
§4.1). The **optimality principle** (Bellman): if J lies on the best path from I to K, then the rest
of that path is the best path from J to K. So the best routes to one destination form a loop-free
**sink tree**, the benchmark every routing algorithm approximates (T&W §5.2.1).

- **Static vs dynamic.** Static routes change only by manual edit and do not react to failure. They
  suit stubs with one exit. Dynamic routing follows topology changes, at the risk of transient loops
  (K&R §5.2; T&W §5.2).
- **Link state (Dijkstra).** Every node floods its link costs, builds the same topology map, and
  computes a least-cost tree (O(n²) basic, faster with a heap). If link costs track load, routes
  **oscillate**; fix this with load-insensitive costs. A faulty router can lie only about its own
  links (K&R §5.2.1). OSPF and IS-IS are link-state protocols.
- **Distance vector (Bellman-Ford).** `d_x(y) = min_v { c(x,v) + d_v(y) }`, exchanged with neighbours
  only. Good news travels fast. Bad news travels slowly: **count-to-infinity** and transient loops.
  Poisoned reverse fixes two-node loops only. One router advertising false costs can poison the whole
  domain (K&R §5.2.2). RIP is distance vector. BGP is path vector, a DV variant.
- **Flooding** sends every packet everywhere. It is maximally robust and is the building block of
  link-state dissemination (T&W §5.2.3).
- **TTL** (hop limit) is decremented at every hop, so a looping packet dies instead of circulating
  forever (K&R §4.3.1).

**Audit lens**
- Static routes used as the only path where redundant links exist: failover will not happen.
- Next hops that do not resolve, or statics pointing at each other, are blackholes and loops.
- Distance-vector IGPs without filtering or authentication: one misconfigured node poisons the domain.

## §6. Hierarchical routing: autonomous systems, OSPF, BGP and policy

To scale and to keep administrative autonomy, routers are grouped into **autonomous systems** under
one administration, each with a globally unique ASN. Routing *within* an AS (intra-AS) is driven by
performance. Routing *between* ASs (inter-AS) is driven by policy and scale. That difference is why
the two use separate protocols (K&R §5.3–5.4).

- **OSPF** (RFC 2328, IP protocol 89) floods link-state advertisements within an **area** and runs
  Dijkstra per router. It uses HELLOs to detect neighbours, ECMP across equal-cost paths, and a
  designated router on LANs. Every area attaches to exactly **one backbone area**, through area border
  routers that summarize between areas. OSPF is **unauthenticated by default**. Simple authentication
  is a cleartext password; keyed hashes with sequence numbers resist forgery and replay. Operators set
  link weights, and setting them is how they engineer traffic (K&R §5.3; T&W §5.6.6). HMAC-SHA
  authentication is RFC 5709 **[beyond texts]**.
- **BGP** is the single inter-AS protocol. It is path vector, over TCP 179, and its routes are prefixes
  plus attributes (K&R §5.4; T&W §5.6.7).
  - **eBGP** runs between ASs, **iBGP** within one.
  - **AS-PATH** prevents loops: a router rejects any route that already contains its own ASN.
  - **NEXT-HOP** ties BGP to the IGP, which supplies the cost of reaching that next hop.
  - Selection, in the books' order: highest local preference (pure policy), shortest AS-PATH, closest
    NEXT-HOP (**hot-potato**, which makes paths asymmetric), then a tie-break. MED, origin and
    eBGP-over-iBGP are further steps **[beyond texts]**.
- **Policy.** A stub or multi-homed customer advertises only its own prefixes, so it never becomes
  transit between its providers. A provider carries traffic only to or from its customers, and does
  not re-advertise one peer's or provider's routes to another. Peering is **not transitive**.
  Together these rules are "valley-free" export (Gao, 2001) (K&R §5.4.5).
- **Anycast** announces one prefix from many sites, so BGP takes each client to the nearest instance.
  It is ideal for DNS. It is risky for long TCP sessions, which can move mid-connection (K&R §5.4.4).

**Audit lens**
- eBGP with no inbound or outbound prefix filter, or no max-prefix limit, accepts or leaks anything:
  hijacks, leaks, memory exhaustion. RPKI and TCP-AO are the modern controls **[beyond texts]**.
- A multi-homed edge re-advertising one provider's routes to another is an unintended transit (a
  route leak).
- OSPF on user-facing interfaces that are not passive, or without authentication, accepts injected
  routes. Non-backbone areas not attached to the backbone break inter-area routing.
- Cloud peering inherits the same rule: peering is not transitive unless a hub routes
  (topology-modeling M2.3).

## §7. Control plane versus data plane: SDN and cloud routing

In **per-router control**, every router runs the routing algorithm. In **logically centralized
control (SDN)**, a controller holds network-wide state and pushes forwarding state to minimal agents.
The controller is physically distributed for reliability (K&R §5.1, §5.5).

- **Generalized forwarding (match-plus-action).** Destination-based forwarding is one special case.
  Flow tables match many L2–L4 fields and apply forward/drop/modify actions, with **priority**
  deciding overlaps. One table can express a router, a switch, a firewall, NAT or a load balancer. A
  packet that matches nothing is dropped or sent to the controller (K&R §4.4). OpenFlow and P4 are
  instances of this model.
- **SDN controller.** It exposes a northbound API to applications and talks southbound to devices
  (OpenFlow on TCP 6653, NETCONF, OVSDB). On a link failure it recomputes and reprograms the affected
  switches. Distribution brings consistency problems, which are solved with consensus (K&R §5.5).
- **Cloud networks are SDN.** VNet and VPC route tables, UDRs, NSGs and peering are match-action state
  programmed by the provider's controller. The "router" of a VNet is implicit. This is why
  topology-modeling M2.2 models UDR next hops as edges.

**Audit lens**
- Overlapping match rules with unclear priority are shadowing risks (segmentation).
- A controller that is a single instance, or an unauthenticated controller channel reachable from the
  data plane, is a High finding. An unrestricted northbound API is Critical.
- A table-miss rule that sends everything to the controller is a DoS vector against it.

## §8. The link layer: ARP, switching, spanning tree and VLANs

- **MAC and ARP.** A MAC address is a flat 48-bit interface identifier. It can be changed in software,
  so it is not an identity. ARP resolves an on-subnet IP address to a MAC with a broadcast query, a
  unicast reply and an expiring cache. For off-subnet destinations a host ARPs for its **default
  gateway**. ARP has no authentication, and caches accept unsolicited (gratuitous) mappings, so any
  host on the segment can poison a neighbour's cache and sit in the middle (K&R §6.4.1; T&W §5.6.4).
  Dynamic ARP inspection is the mitigation **[beyond texts]**.
- **Self-learning switches.** A switch records each frame's *source* MAC against its arrival port.
  For an unknown destination it floods the frame out every other port. **MAC flooding** fills the
  table with fake addresses, so the switch floods everything and a sniffer sees it. Broadcasts (ARP,
  DHCP) always reach the whole broadcast domain (K&R §6.4.3; T&W §4.8.2).
- **Spanning tree.** Redundant L2 links form loops. L2 frames have no hop count, so flooded frames
  circulate and multiply into a **broadcast storm** that saturates the domain. 802.1D (later revised
  for faster convergence) elects the lowest bridge ID as **root**, keeps each bridge's shortest path to
  it, and blocks the remaining ports. The result is exactly one active path between any two stations,
  with redundant capacity left idle (T&W §4.8.3). Root and BPDU guard are **[beyond texts]**.
- **Switches vs routers.** A router bounds the broadcast domain; a switch does not. Switched networks
  are restricted to a tree and generate ARP load. Routers allow rich multipath and act as a barrier to
  storms. The books' rule of thumb: a few hundred hosts can be switched, thousands need routing (K&R
  §6.4.3, Table 6.1).
- **VLANs.** A VLAN is a logical LAN and its own **broadcast domain**. Traffic between VLANs must be
  routed. Membership is usually port-based, and unassigned ports fall into a default VLAN. Trunks
  carry several VLANs using a 4-byte **802.1Q** tag with a 12-bit VLAN ID (K&R §6.4.4; T&W §4.8.5).
  Native-VLAN double tagging and rogue trunk negotiation are the VLAN-hopping attacks **[beyond
  texts]**.
- **MPLS** forwards on short labels along pre-established paths. It enables traffic engineering, fast
  reroute and provider VPNs. MPLS VPNs **separate** traffic but do not **encrypt** it (K&R §6.5.1;
  T&W §5.6.5).

**Audit lens**
- "Same VLAN or subnet" means same blast radius. Different trust levels sharing an L2 domain is High.
- Redundant L2 links without loop control is High. A root bridge left to chance is Medium.
- Trunks that allow all VLANs, a native VLAN that is also a user VLAN, and production in the default
  VLAN are all findings.
- MAC allow-lists are weak authentication. "Switched, so nobody can sniff" is false under flooding.

## §9. Data-center and fabric topologies

Classic data-center networks are trees: border routers, then access routers, then aggregation tiers,
then top-of-rack (ToR) switches. Trees scale, but they throttle traffic *between* racks. In K&R's
example, 40 rack-to-rack flows share one 100 Gb/s uplink and get 2.5 Gb/s each against 10 Gb/s NICs:
an effective 4:1 **oversubscription** (total host-facing bandwidth over uplink bandwidth at a tier)
(K&R §6.6.1).

Modern fabrics are multistage **Clos** networks (Clos, 1953): many small switches, richly connected
between tiers, with **ECMP** spreading flows over many equal-cost paths. The loss of one spine costs
capacity, not reachability (K&R §6.6.2). A fat-tree is a Clos with full bisection bandwidth, i.e. 1:1
**[beyond texts]**. Redundancy also comes from dual-homed ToRs, duplicated tiers and availability
zones.

**Audit lens**
- Single-homed ToRs, one load balancer, or one border router in a production tier are articulation
  points (G4).
- Undocumented or high oversubscription on east-west or storage tiers is an SLO risk. Actual load is
  🔬.
- In clouds, availability zones are the fabric's failure domains. Zonal services without
  zone-redundant peers are shared fate (resilience.md).

## §10. Inside the router: queues, buffers and QoS

A router has input ports (where the forwarding-table lookup happens, against a shadow copy of the
table on each line card), a switching fabric, output ports with queues and a scheduler, and a routing
processor that runs the control plane (K&R §4.2).

- **Queueing.** Queues form at the input when the fabric is slower than the ports combined, and at
  the output when many inputs converge on one output. With FIFO input queues, head-of-line blocking
  limits throughput to about 58% of capacity. When buffers fill, packets drop (K&R §4.2.4).
- **Buffer sizing.** The rule of thumb is `B = RTT·C`, or `RTT·C/√N` with N flows. Too little buffer
  loses packets. Too much adds standing delay (**bufferbloat**). Active queue management (RED, PIE,
  CoDel) drops or ECN-marks packets early. Infinite buffers make congestion *worse*, because packets
  expire while they wait (T&W §5.3).
- **Scheduling.** FIFO; strict priority, which can starve lower classes; round robin; **WFQ**, which
  guarantees class i at least `R·wᵢ/Σwⱼ` (K&R §4.2.5).
- **Shaping and policing.** A **token bucket** with rate R and depth B bounds the long-term rate at R,
  and lets bursts of up to B through. The maximum burst duration is `S = B/(M − R)` at peak rate M.
  Shaping queues the excess; policing drops or re-marks it. **DiffServ** marks classes at the ingress
  (EF for low-latency traffic, AF classes with drop precedence). Markings must be **policed** at
  trust boundaries, or everyone marks their own traffic as important (T&W §5.4).

**Audit lens**
- A strict-priority or EF queue with no policer starves every other class.
- DSCP trusted from untrusted hosts with no re-marking lets any tenant claim priority.
- Control-plane traffic not protected from data-plane floods (no CoPP or rate limit on punted
  packets) can overwhelm the routing processor.
- Rate limits with a burst parameter that doesn't match the intended SLA.

## §11. Security principles

Secure communication has four goals (K&R §8.1):
- **Confidentiality:** only the endpoints can read the message.
- **Message integrity:** tampering is detected.
- **Endpoint authentication:** each side proves who it is.
- **Operational security:** the organization's network itself is protected from attack.

The intruder model is an attacker who can eavesdrop, and also modify, insert or delete messages.
These goals apply to infrastructure (DNS, routing exchanges, management traffic) as much as to user
data.

The design principles the rubrics cite:

- **Default-deny.** Only explicitly allowed traffic passes, so the allow rules *are* the policy. The
  textbook ACL ends in deny-all (K&R §8.9.1).
- **Least privilege.** Every allowed flow is as narrow as its purpose requires in source, destination,
  protocol and port.
- **Defense in depth.** A single perimeter fails all at once: insiders bypass it, encryption blinds
  it, spoofing fools address-based trust. So controls are layered: perimeter, internal segmentation,
  host firewalls, encryption, monitoring (T&W §8.6.2).
- **The original Internet trusted everyone** (K&R §1.6). By default anyone can send to anyone, and
  claimed identities (source addresses) are not verified. Trust based only on a source address is
  therefore weak.

**Audit lens**
- Tag every security finding with the goal it breaks. Plaintext SNMP v1/v2c, Telnet and
  unauthenticated routing break integrity and authentication of the *control plane*.
- A design that relies on one boundary — "on the VPN means trusted", "inside the NAT means safe" — is
  a defense-in-depth failure.

## §12. Filtering: firewalls, the DMZ and IDS/IPS

A firewall sits between a protected network and the outside, and must meet three conditions: all
traffic passes through it, only authorized traffic is allowed, and it cannot itself be penetrated. A
compromised firewall is worse than none, because it gives false assurance (K&R §8.9.1; T&W §8.6.2).

- A **stateless packet filter** judges each packet alone. It can match protocol, addresses, ports,
  TCP flags, ICMP type, direction and interface, using ACLs evaluated top to bottom. Rules like "allow
  inbound with ACK set" admit crafted packets.
- A **stateful filter** keeps a connection table (handshake to FIN, plus an idle timeout) and admits
  return traffic only for connections it saw open. Its consequence is that **both directions must
  pass the same firewall**: an asymmetric path drops half the flow (routing.md).
- An **application gateway (proxy)** relays a specific application. It can authenticate *users* and
  inspect content, at a per-application and performance cost.
- A **DMZ** is a lower-trust segment for internet-facing servers. It is reachable from outside, and
  its own access inward is tightly restricted.
- An **IDS** inspects packets deeply and alerts. An **IPS** also blocks. Signature-based detection
  misses new attacks; anomaly-based detection struggles to separate unusual from malicious. Sensors
  are distributed (DMZ and internal zones) and report centrally (K&R §8.9.2).
- **Firewall limits** (T&W §8.6.2). They rely on port conventions; encryption blinds them; insiders
  are already inside; and they cannot stop floods of legitimate-looking traffic.

**Audit lens**
- An implicit allow, or a final `allow any any`, is Critical or High. So are internet sources allowed
  to management or data ports.
- A broad allow above a specific deny shadows the deny, so the control looks present and isn't.
- A DMZ host with broad access inward collapses the DMZ.
- No egress filtering; no IDS or flow visibility at internet ingress; encrypted traffic with no
  inspection point. State the coverage gap.

## §13. Secure channels: TLS, IPsec, VPNs and wireless

- **TLS** adds confidentiality, integrity, server authentication and optional client authentication
  over TCP (K&R §8.6).
  - The handshake negotiates cipher suites, verifies the server's **certificate** against a CA, and
    derives separate keys per direction from nonces and a shared secret.
  - A MAC over the whole handshake defeats **downgrade**. Per-record sequence numbers defeat reordering
    and replay. An authenticated close defeats truncation.
  - Current practice is TLS 1.2 or later; TLS 1.3 requires ephemeral (EC)DHE for forward secrecy and
    AEAD ciphers **[beyond texts]**.
- **IPsec** protects IP datagrams between two network-layer endpoints (K&R §8.7; T&W §8.6.1).
  - Traffic flows over one-way **Security Associations** (SAs), held in the SAD. The SPD decides which
    traffic is protected.
  - **AH** (protocol 51) gives integrity and origin authentication but no confidentiality, and is
    largely historical. **ESP** (protocol 50) gives confidentiality and integrity. A null cipher is
    permitted, and is a finding.
  - **Transport mode** protects the payload host to host. **Tunnel mode** wraps the whole packet
    between gateways, and is the VPN mode.
  - Sequence numbers defeat replay and force rekeying.
  - **IKE** builds a Diffie-Hellman SA, then authenticates peers inside it, then derives the IPsec SAs.
    Use IKEv2, because v1 had serious flaws. Current practice: AES-GCM, SHA-2, DH group ≥ 14 or ECDH,
    PFS on, certificates over widely shared PSKs **[beyond texts]**.
- **VPNs** give private-network properties over a public network, with crypto handled only at the
  gateways (K&R §8.7.1; T&W §8.6.3). A VPN can be "logically secure" and still leak through paths that
  bypass it. A VPN is an encrypted pipe, not a trust grant.
- **Wireless.** Radio goes straight past the firewall, so 802.11 needs its own mutual authentication
  and encryption (K&R §8.8; T&W §8.6.4).
  - **WEP is broken**: its keystreams are reused and its integrity check is a CRC. WPA/TKIP is broken
    too.
  - **WPA2** (CCMP, AES) derives per-client keys in a four-way handshake.
  - With a shared passphrase ("personal"), every client can derive the others' keys. **802.1X/EAP**
    ("enterprise") gives per-user credentials.
  - **WPA3** fixes the handshake nonce-reuse attack and strengthens keys.

**Audit lens**
- Certificate verification disabled is Critical/High. So are legacy protocol versions and suites.
- ESP null or AH alone where confidentiality is required; IKEv1 aggressive mode; weak DH groups; PSKs
  shared across many peers.
- A crypto ACL/SPD too narrow (some traffic leaves in clear) or `any any`.
- WEP, TKIP or open SSIDs bridged inward; WPA2-PSK on corporate networks; guest wireless not
  firewalled from internal zones.
- Split tunnelling on remote access lets a compromised home network bridge in.

## §14. Network management, ICMP and visibility

- **The management framework.** A managing server, managed devices, an agent on each device, device
  data and a protocol (K&R §5.7.1). Device data is of three kinds: **configuration** (set by an
  operator), **operational** (learned, e.g. neighbours) and **statistics** (counters). Devices are
  managed three ways:
  - CLI over console, Telnet or SSH: vendor-specific and error-prone at scale.
  - SNMP/MIB: mostly monitoring, one device at a time.
  - NETCONF/YANG: network-wide, model-validated, transactional configuration (RFC 3535's
    requirements).
- **SNMP** is request-response over UDP (port 161, traps on 162 **[beyond texts]**), reading and
  writing MIB objects, with traps for events (K&R §5.7.2). v1 and v2c authenticate with cleartext
  **community strings** **[beyond texts]**. Because v1 lacked security, SNMP was used mostly for
  reads. **v3** adds authentication and privacy (authPriv).
- **NETCONF** (RFC 6241) is XML RPC over a secure session: SSH per RFC 6242 **[beyond texts]**, TLS in
  the book. Its operations are `get-config`, `get`, `edit-config` with rollback, `lock`/`unlock`, and
  subscriptions. Operations combine into atomic multi-device transactions. **YANG** (RFC 6020) models
  configuration and state with constraints (K&R §5.7.3).
- **ICMP** (IP protocol 1) carries errors and diagnostics: echo, destination unreachable, TTL
  exceeded. Traceroute relies on TTL exceeded (K&R §5.6). **Path-MTU discovery** depends on ICMP:
  "fragmentation needed" for IPv4 (RFC 1191) and ICMPv6 **Packet Too Big** (RFC 8201). IPv6 routers
  never fragment, so in IPv6 PMTUD is mandatory.
- **Visibility.** Syslog to a central collector, flow records (NetFlow/IPFIX, cloud flow logs),
  synchronized time (NTP) so events correlate, and traps or informs for failures. A network that
  cannot be observed cannot be audited at runtime (🔬 flags pile up).

**Audit lens**
- Telnet, HTTP management, SNMP v1/v2c (worse with `public`/`private` or write access) and SNMPv3
  without authPriv are all findings, as is a management plane reachable from production or internet
  zones.
- Blanket ICMP/ICMPv6 denies break PMTUD and IPv6 neighbour discovery. Allow at least type 3, type 11
  and Packet Too Big; rate-limit echo rather than blocking it.
- Tunnels with no MSS clamping.
- Hand-made CLI changes with no source-controlled configuration mean drift and nothing to audit
  against.

## §15. Attacks on networks

From K&R §1.6, with the L2 attacks of T&W §4.8 and K&R §6.4:

- **Malware and botnets.** Compromised hosts are enrolled as attack sources. Self-replicating malware
  spreads like an epidemic over the contact graph (G9).
- **Denial of service.**
  - Vulnerability attacks: a few crafted packets.
  - Bandwidth floods: ~R of traffic saturates an access link of rate R. Distributed sources (DDoS) are
    harder to filter.
  - Connection floods: the SYN flood is the classic, and SYN cookies are the defense.
- **Sniffing** is passive, so hard to detect. It works on wireless, on broadcast media, and on any
  compromised link. The defense is encryption.
- **Spoofing.** Forged source addresses are forwarded normally. The defenses are endpoint
  authentication and ingress filtering (BCP 38 / uRPF **[beyond texts]**).
- **L2 attacks:** ARP poisoning, MAC flooding, rogue DHCP, rogue root bridge, VLAN hopping (§8).
- **Control-plane attacks:** injected routes into unauthenticated IGPs, BGP hijacks and leaks (§6),
  and floods of punted packets against the routing processor (§10).

**Audit lens**
- An internet edge with no anti-spoofing, no SYN-flood or DDoS protection, or trust based only on
  source address is High.

## §16. Literature

- J. F. Kurose and K. W. Ross, *Computer Networking: A Top-Down Approach*, 8th ed., Pearson, 2021.
  Ch. 1 (core, delay, layering, attacks), 4 (data plane, addressing, NAT, IPv6, SDN, middleboxes), 5
  (routing, OSPF, BGP, SDN control, ICMP, management), 6 (link layer, VLANs, data centers), 8
  (security, TLS, IPsec, wireless, firewalls, IDS).
- A. S. Tanenbaum and D. J. Wetherall, *Computer Networks*, 5th ed., Pearson, 2011. §1.4 (reference
  models), §4.8 (switching, spanning tree, VLANs), §5.2–5.4 (routing algorithms, congestion, QoS),
  §5.6 (IP, CIDR, NAT, OSPF, BGP), §8.6 (IPsec, firewalls, VPNs, wireless).
- J. H. Saltzer, D. P. Reed and D. D. Clark, "End-to-end arguments in system design," *ACM TOCS*,
  1984.
- L. Gao, "On inferring autonomous system relationships in the Internet," *IEEE/ACM ToN*, 2001.
- RFCs cited for facts beyond the texts: 1191, 1918, 1958, 2328, 2827 (BCP 38), 3234, 3535, 4213,
  4443, 5709, 6020, 6241, 6242, 6598, 8201.

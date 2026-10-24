# Graph Theory — The Network-Science Lens

> The analytic lens for topology, as relational theory is for a schema. A network's devices, networks
> and links form a graph. A handful of graph quantities answer the resilience questions an audit has
> to settle: what is a single point of failure, how many failures a service survives, where the
> chokepoints are, and how the network behaves under random versus targeted failure. Sections G1–G12
> are cited by the rubrics, especially [`resilience.md`](../netaudit/resilience.md). The harness
> (`harness/netgraph.py`) computes the metrics from `topology.json`
> ([`topology-modeling.md`](topology-modeling.md)). Networking terms are in
> [`theory.md`](theory.md).
>
> Sources: **Newman** = M. E. J. Newman, *Networks*, 2nd ed. (2018); **Barabási** = A.-L. Barabási,
> *Network Science*, ch. 6 "Evolving Networks" (2016). Everything is paraphrased. Standard results
> neither text states are marked **[standard]**.

## G1. Topology as a graph

A network is a set of **vertices** (nodes) and **edges** (links), stored as an adjacency matrix
(`A_ij = 1` when i and j are linked) or as adjacency lists. Edges may be weighted (capacity, cost) or
directed (Newman §6.1–6.4). The same Internet can be mapped at the level of routers, subnets, domains
or autonomous systems. Each is a different graph with different metrics, and maps assembled from
sampled paths miss edges (Newman §2.1).

**For a network audit**
- **Fix the granularity before computing anything, and record it.** One node per HA cluster hides the
  redundancy inside it. One node per member overstates redundancy when the members share state,
  config or control plane. `topology.json` uses one node per member, plus `attrs.shared_fate` groups,
  so both readings are available (topology-modeling M1).
- **Undirected** for physical and L3 adjacency, which is what the resilience metrics use. **Directed**
  for policy reachability (flows, UDRs, non-transitive peering, one-way VPN selectors).
- A config or IaC export is a sample, as a traceroute is. Missing links make the topology look *more*
  fragile, and stale links make it look *more* robust. Report the evidence coverage beside every
  metric.

## G2. Degree, hubs and concentration

The **degree** `k_i = Σ_j A_ij` is the number of links at a node, and the mean degree is
`⟨k⟩ = 2m/n`. The **degree distribution** `p_k` is the fraction of nodes with degree k. It is best read
cumulatively, as the fraction with degree ≥ k, to avoid binning artefacts. Real networks are usually
right-skewed, with a tail of **hubs**: in Newman's AS-level Internet data, about 3.3% of nodes hold
half of all connections (Newman §6.9, §7.1, §8.3).

A **concentration curve** W(P) answers "what share W of link endpoints attaches to the top share P of
nodes?". It can be computed directly from data with no distributional assumption (Newman §8.4.2). The
**heterogeneity** `⟨k²⟩/⟨k⟩` is the number that drives fragility under attack (G9).

**For a network audit**
- Report the maximum degree as a share of n, the share of link endpoints on the top 10% of nodes
  (**hub concentration**), and `⟨k²⟩/⟨k⟩`. A few nodes holding most endpoints is the structural
  signature of a network that a hub failure or compromise can take apart.
- Degree measures how *exposed* a node is, not whether it is a chokepoint. A low-degree node joining
  two groups can matter more (G6).

## G3. Paths, components and trees

- A **path** is a sequence of linked nodes. **Geodesic** distance is the length of the shortest path.
  BFS finds hop distances in O(m + n). Dijkstra handles non-negative weights (Newman §10.3–10.4).
- A **component** is a maximal set of nodes joined pairwise by paths. In a directed graph:
  - **strongly connected components** have paths both ways between every pair;
  - a node's **out-component** is everything it can reach;
  - its **in-component** is everything that can reach it (Newman §6.11).
- A **tree** is connected and loop-free with exactly `n − 1` edges. There is one path between any
  pair, so **every edge is a bridge and every interior node is an articulation point** (Newman §6.7).
  The **cyclomatic number** `m − n + c` (c components) counts independent loops: the spare edges
  beyond a spanning forest **[standard]**.

**For a network audit**
- More than one component means islands. Each one is either intended segmentation (air-gapped OT, an
  out-of-band management network) or a defect (an orphaned VNet, a missing peering, a dead tunnel).
  Ask about intent before calling it a finding.
- On the directed policy graph, the out-component of an internet-facing node is its **potential
  lateral-movement reach**. The in-component of a data zone is **everything that can reach it**.
- A cyclomatic number near zero means a near-tree: every interior device is a SPOF. It is a cheap
  headline, but it does not say *where* the redundancy is. Always pair it with G4.
- **Path stretch.** Recompute critical-pair distances after a simulated failure. A pair that survives
  on a much longer or *uninspected* path is still a finding (Newman §10.3).

## G4. Articulation points, bridges and bicomponents

- An **articulation point** (cut vertex) is a node whose removal disconnects the graph or a pair. It
  is a vertex cut set of size 1.
- A **bridge** is an edge whose removal does the same. It is an edge cut set of size 1. Parallel edges
  between the same two nodes are never bridges.
- A **bicomponent** is a maximal set in which every pair has at least two vertex-independent paths.
  Articulation points are where bicomponents meet.
- More generally, k-components nest inside each other: tricomponents inside bicomponents inside
  components (Newman §6.12, §7.8.2).
- One linear-time depth-first search finds all articulation points and bridges (Hopcroft–Tarjan)
  **[standard]**.

**For a network audit**
- **Articulation point = single-point-of-failure device**: a router, firewall, hub VNet, gateway, DNS
  forwarder or core switch whose loss partitions the network. **Bridge = single-point-of-failure
  link**: one circuit, one peering, one tunnel.
- **Rank each one by blast radius**: the size of the smaller side of the split, or the number of
  critical pairs it separates. Don't just list them.
- **Shared fate.** Contract every `shared_fate` group to one node and recompute. An articulation point
  that appears only after contraction is a **false-redundancy** finding (resilience.md). A graph SPOF
  that is internally redundant in a way the model doesn't show is "SPOF by model, verify HA": ⚠️, not
  ✅.
- A bridge to a leaf (a single-homed branch) may be an accepted risk. A bridge in the middle of the
  graph rarely is.

## G5. Independent paths, Menger's theorem and max-flow

Two s–t paths are **edge-independent** if they share no edge, and **vertex-independent** if they
share no vertex other than s and t. The number of independent paths is the pair's **edge connectivity
λ(s,t)** or **node connectivity κ(s,t)**. A **cut set** is a set of edges or vertices whose removal
separates s from t.

**Menger's theorem:** the size of the minimum cut set equals the number of independent paths, for
both the edge and vertex versions (Newman §6.12).

**Max-flow/min-cut.** With unit capacities, three quantities are equal: the number of edge-independent
paths, the minimum edge cut and the maximum s–t flow. With real capacities, the maximum flow equals the
minimum total capacity of a cut (Newman §6.12.1, §10.5).

How to compute them:
- **Edge connectivity:** augmenting paths over the residual graph (Ford–Fulkerson with BFS).
- **Node connectivity:** split each intermediate node v into `v_in → v_out` with a unit-capacity arc,
  then run edge max-flow.
- **The minimum cut itself:** the edges leaving the set of nodes reachable from s in the final
  residual graph.
- **Upper bound:** `min(k_s, k_t)`. A pair never has more disjoint paths than its less-connected end
  has links.

**For a network audit**
- **κ(s,t) for a critical pair is the number of independent device failures it survives, plus one.**
  κ = 1 means a SPOF on the path. κ = 2 means it survives any single device loss. λ(s,t) answers the
  same question for links. The gate requires κ ≥ 2 for every critical pair (scoring.md).
- **Report the cut set, not just the number**: it names exactly what to harden.
- **N+1 in bandwidth, not only topology.** Capacity-weighted max-flow shows whether the surviving paths
  can carry the load. Link capacities are ⚠️ from config; actual load is 🔬.
- `min(k_s, k_t)` gives a quick finding: a single-homed endpoint caps κ at 1, whatever the core looks
  like.
- **Disjoint in the graph is not disjoint in the world.** One conduit, one power feed, one region, one
  carrier or one config pipeline can sit under two "independent" paths. Model them as `shared_fate`,
  or κ is overstated.
- **Adjacent endpoints.** When s and t are directly linked, count the direct link as one path, remove
  it, and add the κ of the rest.

## G6. Betweenness: chokepoints and blast radius

**Betweenness centrality** is `x_i = Σ_st n^i_st / g_st`, where `n^i_st` is the number of shortest
s–t paths through i and `g_st` the total number of shortest s–t paths. It is proportional to the
traffic through i if every pair exchanges traffic equally along shortest paths. It is normalized to
[0, 1] by the number of pairs. **Brandes' algorithm** computes it in O(n(m + n)) unweighted: one BFS
per source, then a backward accumulation of path counts. Edge betweenness is defined the same way over
edges (Newman §7.7, §10.3.6).

Betweenness has a very wide range, from a leaf's minimum to a star centre's maximum. A low-degree
**broker** on the only link between two groups can have the highest betweenness of all. **Closeness**
(inverse mean distance) and **eigenvector** centrality ("linked to well-linked nodes") exist too, but
they rank poorly on small engineered graphs (Newman §7.2, §7.6).

**For a network audit**
- High betweenness marks a **chokepoint and blast-radius hotspot**: the node most communicating pairs
  traverse. **A node can be redundant (κ ≥ 2 around it) and still be a chokepoint.** Its failure is
  survivable, but it is the inspection, capacity and compromise hotspot, and its backup takes the
  whole surge on failover. Report betweenness and connectivity together.
- A high-betweenness, low-degree node is a hidden broker the inventory may not flag: a jump host, a
  transit VNet peered between two hubs.
- High edge betweenness singles out the interconnect worth doubling.
- **Topology is not routing.** OSPF costs, BGP policy, UDRs and forced tunnelling decide real paths.
  Hop-count betweenness is a structural prior, not a traffic forecast. Label it "structural", or weight
  edges by the routing metric.

## G7. Clustering and assortative mixing

The **clustering coefficient** is `C = 3 × triangles / connected triples`: the probability that two
neighbours of a node are themselves linked. The local version is `C_i = triangles(i) /
(k_i(k_i − 1)/2)`. **Assortativity** r is the correlation between the degrees at the two ends of an
edge, in [−1, 1]. Technological networks, the Internet included, are typically **disassortative**
(r < 0): hubs connect mostly to low-degree nodes (Newman §7.9, §7.13, §8.6–8.7).

**For a network audit**
- Triangles are local redundancy: a mesh among core switches, a triangle of site interconnects.
- Very low C together with strongly negative r is the fingerprint of **hub-and-spoke**: every spoke
  depends on the hub, and there is no spoke-to-spoke alternative.
- Clustering only sees detours of length two. It is no substitute for G5.

## G8. Degree distributions and power laws: what not to claim

A **power-law** degree distribution `p_k ∝ k^−α`, with α typically 2–3 and only in the tail, is called
**scale-free**. For 2 < α < 3, the mean is finite but `⟨k²⟩` grows without bound as the network grows.
Newman's estimates for the Internet are around 2.1–2.5. Newman warns that least-squares fits to
log-log plots are biased, and gives a maximum-likelihood estimator instead (Newman §8.4, §13.10).
Barabási adds that real growth processes (initial attractiveness, deletion, fitness) bend the tails, so
the defensible question is often only **bounded versus heavy-tailed** (Barabási §6.6).

**For a network audit**
- **Do not call an enterprise or cloud topology "scale-free."** With tens to hundreds of nodes the
  tail has a handful of samples, so an exponent estimate is noise.
- The defensible statement is concentration: "the top X nodes carry Y% of link endpoints;
  `⟨k²⟩/⟨k⟩ = Z`" (G2). That is what drives attack fragility, and it needs no distributional
  assumption.
- Hub-and-spoke designs are heavy-tailed **by construction** (G10), not because of a scale-free growth
  process.

## G9. Percolation and resilience: random failure versus targeted attack

**Percolation** removes nodes (site percolation) or edges (bond percolation) and asks what stays
connected. A large network has a **giant component** above a threshold, and only small fragments
below it. A communication network functions while a giant component exists (Newman §16.1).

- **Molloy-Reed.** A random graph with a given degree sequence has a giant component if and only if
  `⟨k²⟩/⟨k⟩ > 2` (Newman §13.8).
- **Random removal.** The critical occupation is `φc = ⟨k⟩ / (⟨k²⟩ − ⟨k⟩)`. The more heterogeneous the
  degrees, the lower φc, so heavy-tailed networks survive the random loss of most of their nodes
  (Newman §16.2).
- **Targeted removal** takes nodes in decreasing order of degree (Newman §16.3–16.4).
  - Heavy-tailed networks collapse after a small fraction. In Newman's simulation of the real
    Internet, the largest cluster is essentially gone after removing about 5% of the highest-degree
    nodes.
  - Networks without big hubs (power grids, road networks) show little difference between random and
    targeted removal.
  - Hub-dominated networks are **robust to random failure and fragile to attack on hubs**.
- **Simulate on real graphs.** Remove nodes in random order many times, breaking ties randomly, and
  average the largest-component size. Union-find gives the whole curve in about one pass (Newman
  §16.5).

**For a network audit**
- The harness plots the **robustness curve** — the largest-component fraction, and the share of
  critical pairs still connected, against the fraction of nodes removed — under three removal orders:
  - **random** (independent hardware failure);
  - **highest-degree first** (an outage or attack on hubs);
  - **highest-betweenness first** (an attack on chokepoints).
- **The gap between the random and targeted curves is the finding.** A large gap means resilience
  rests on a few hubs, so those hubs must be redundant, independently failing, segmented and hardened.
  A small gap means the network degrades gracefully.
- Also report how many targeted removals it takes to disconnect the first critical pair. That number
  is easier to act on than the curve.
- The thresholds are exact only for large, randomly wired graphs. On a small engineered network, the
  simulation is the evidence and the formulas are interpretation (G12).
- Recomputing the ranking after each removal (**adaptive attack**) is usually more damaging and closer
  to what an attacker does **[standard]**. State which variant was used.
- The same structure governs spread. Malware moves over the reachability graph like an epidemic over
  a contact network (Newman ch. 17), so high-betweenness, high-degree nodes are also where
  containment pays most (theory §15).

## G10. How hub dependence accumulates: growth, fitness and decline

- **Preferential attachment** (Barabási–Albert). Each new node attaches to existing nodes with
  probability proportional to their degree. The result is a heavy tail (exponent 3) and a
  **first-mover advantage**: the oldest nodes become the largest hubs (Newman §14.2; Barabási §6.1).
- **Fitness** (Bianconi–Barabási). Attachment is proportional to `η_i k_i`, the product of an intrinsic
  **fitness** and the degree. Fitter late arrivals overtake older hubs, and small fitness differences
  are amplified by growth (Barabási §6.2–6.3).
- **Condensation.** For some fitness distributions, the fittest node captures a *finite fraction of
  all links*. The network becomes hub-and-spoke, and the hierarchy of hubs disappears ("winner takes
  all") (Barabási §6.4).
- **Designed hubs.** Some networks are hub-and-spoke because they were **optimized** for a trade-off
  between link cost and path length, like airline route maps. Growth does not explain them (Newman
  §14.6).
- **Other evolving processes** (Barabási §6.5), qualitatively:
  - initial attractiveness and random internal links *homogenize* the network;
  - new links preferentially joining existing hubs *concentrate* it;
  - node deletion homogenizes it;
  - aging that favours young nodes erodes old hubs.
- **Decline.** In a shrinking network (Barabási's New York garment-district example), links were lost
  "weak gets weaker": peripheral nodes lost links first. The largest component collapsed while the
  degree distribution looked unchanged (Barabási §6.5).

**For a network audit**
- **Organic growth concentrates dependence.** The new VNet peers to the hub that already has the
  routes. The new site tunnels to the firewall that already terminates the others. The new app goes
  behind the existing load balancer. Nobody designs the resulting hub dependency. The first-mover
  effect means the oldest core device is usually the biggest hub, and often the one with the oldest
  hardware or firmware.
- **Fitness in IT** is whatever makes a node the natural attachment point regardless of age: the
  mandated inspection point, the gateway with the circuit, the box the team knows. A policy like "all
  traffic traverses the central firewall" deliberately produces the condensate. That is often the right
  design, but it moves all resilience into one node, so the audit must verify that node's redundancy,
  κ around it for every critical pair, its betweenness share, and its behaviour under targeted removal.
- **Never "you have a hub."** The finding is "the hub is (or isn't) redundant, and its failure or
  compromise affects X% of critical pairs."
- **Decommissioning strips secondary links first** (backup tunnels, second circuits), quietly making
  peripheral sites single-homed while the degree histogram barely moves. Re-run G4 and G5 after every
  change. With config history (git), the growth of each device's link count over time shows which
  nodes are on a runaway trajectory (audit-lenses §6).

## G11. The Laplacian and algebraic connectivity

The graph **Laplacian** is `L = D − A`, where D is the diagonal degree matrix. The number of zero
eigenvalues equals the number of components. The second-smallest eigenvalue `λ₂`, the **algebraic
connectivity**, is non-zero exactly when the graph is connected. Its eigenvector (the Fiedler vector)
splits the graph along its weakest seam (Newman §6.13, §11.5). For non-complete graphs,
`λ₂ ≤ κ(G)` **[standard]**.

**For a network audit**
- Use λ₂ to **compare designs**: before vs after, option A vs option B. Don't use it as an absolute
  grade, because it depends on n and is hard to explain. The Fiedler split can point at a thin
  interconnect between two sites. G4 and G5 are more actionable.

## G12. Caveats, and which metric answers which question

1. **Scale.** The asymptotic results (thresholds, exponents, condensation) assume large, randomly
   wired networks. IT topologies are small and engineered. Use the exact combinatorial metrics (G4,
   G5) and simulation (G9) as evidence, and the theory as interpretation.
2. **Topology is not routing.** Shortest paths, betweenness and reachability must follow the routing
   and policy model, or be labelled structural.
3. **Hidden shared risk.** Disjointness is only as good as the `shared_fate` modelling.
4. **Granularity.** HA pairs, stacks and clusters change the answer. State the choice (G1).
5. **Redundancy is not centrality.** κ ≥ 2 means not a SPOF; high betweenness can still mean a
   chokepoint. Report both.
6. **Evidence coverage.** Missing links inflate fragility; stale links hide it.

| Metric | Question it answers | Source |
|---|---|---|
| Components, in- and out-components | Are there islands? What can reach what? | Newman §6.11 |
| Cyclomatic number | Is there any path diversity at all? | Newman §6.7 |
| Articulation points, bridges | Which single device or link failure partitions the network, and how badly? | Newman §6.12, §7.8.2 |
| κ(s,t), λ(s,t), the cut set | How many failures does this critical service survive? What exactly to harden? | Newman §6.12, §10.5 |
| Capacity-weighted max-flow | Can the surviving paths carry the load? | Newman §6.12.1 |
| Degree, hub concentration, ⟨k²⟩/⟨k⟩ | How concentrated is dependence on a few hubs? | Newman §8.3–8.4 |
| Betweenness (node, edge) | Where are the chokepoints and blast-radius hotspots, even when redundant? | Newman §7.7 |
| Clustering, assortativity | Is redundancy local (meshes), or is it hub-and-spoke? | Newman §7.9, §7.13 |
| Path stretch after failure | Does the service survive at acceptable latency, through inspection? | Newman §10.3 |
| Robustness curves | Is resilience spread out or concentrated? How fast does it collapse under attack? | Newman ch. 16 |
| Growth, fitness, condensation, decline | Why did hub dependence accumulate, and which change policy makes it worse? | Newman §14; Barabási ch. 6 |
| Algebraic connectivity λ₂ | Which of two designs is better knit, and where is the weakest seam? | Newman §6.13 |

### Literature

- M. E. J. Newman, *Networks*, 2nd ed., Oxford University Press, 2018. Ch. 6 (mathematics of
  networks), 7 (measures and metrics), 8 (large-scale structure), 10 (fundamental algorithms), 13–14
  (random graphs, network formation), 16 (percolation and resilience).
- A.-L. Barabási, *Network Science*, Cambridge University Press, 2016. Ch. 6, "Evolving Networks".
- U. Brandes, "A faster algorithm for betweenness centrality," *J. Math. Sociology*, 2001.
- R. Albert, H. Jeong and A.-L. Barabási, "Error and attack tolerance of complex networks," *Nature*,
  2000.
- J. Hopcroft and R. Tarjan, "Efficient algorithms for graph manipulation," *CACM*, 1973.

Answer key for `net-diagram/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.

# net-diagram — `netdiagram` from a target model (eval 18)

The model (`design/topology.json`, Contoso, 16 nodes, 7 zones, 6 allow flows, 6 default-deny flows) is cloud-only: the one on-prem element, `onprem-dc`, is `inferred:` and has no device evidence.

| # | Planted | Catches a run that… |
|---|---|---|
| 1 | Cloud-only scope | draws a `physical-topology.drawio` anyway — L1/L2 is required only with on-prem device evidence |
| 2 | Stable semantic IDs in the model | lets draw.io generate cell IDs (`2`, `3`, …), so the drawing can't be cross-checked against the model |
| 3 | `onprem-dc` is inferred | draws it like a fact (no dashed outline) |
| 4 | Six deny flows, one per zone | draws deny flows as arrows, or leaves zones without a default-deny badge |
| 5 | The design rev is the source of truth | "fixes" the model while drawing it — `design/` must stay byte-identical |

The conventions checked are diagram-conventions.md §1–§4: the exact file and page names, a legend containing `Network diagram conventions`, a CIDR in every network container's label, and arrows that are exactly the `allow` flows.

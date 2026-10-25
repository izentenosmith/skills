Answer key for `tf-design/`. It lives **outside** the fixture folder on purpose.

# tf-design — `terraform` in Design mode (eval 22)

Only a requirements document. Nothing in it says how to lay out state; the traps are in what it
implies and in what leadership asks for.

| # | Planted | The design should… | Catches a run that… |
|---|---|---|---|
| 1 | Components change at very different rates and are owned by different teams | split state by lifecycle/ownership (network, each service, observability) per environment (T7) | puts everything in one root per environment |
| 2 | Payments is in PCI scope; auditors want its changes and changers separable | give payments its own state, its own apply role, ideally its own repo or root with separate access (T7, T14) | treats payments like any other service |
| 3 | Leadership asks for "one workspace per environment, all in one state bucket" | decline it with a reason (workspaces share one backend and one access policy; prod isolation; account-per-env already exists) and use per-account backends (T7, design-patterns §3) | adopts the ask as stated |
| 4 | Admins apply from laptops | apply from CI with OIDC roles per account, saved plans, prod approval; humans read-only in prod with break-glass (T12–T14) | leaves the laptop path in place |
| 5 | The orders database was deleted and recreated by mistake | `prevent_destroy` / `deletion_protection` / snapshots on stateful resources and a destroy guard in the pipeline (T8, T17) | doesn't address destructive-change protection |
| 6 | Services need the network's IDs | a narrow cross-state interface (SSM parameters or tagged data-source lookups), not wholesale `terraform_remote_state` (design-patterns §5) | — |
| 7 | "A new service in under a day" | a reusable, versioned service module and a thin per-service root (T9, T10) | — |
| 8 | DR region next year | mentioned as an open question or a region dimension in the layout | — |

Safety invariant: Design writes no `resource` blocks (interface skeletons — variables, outputs, backend, versions — are allowed).

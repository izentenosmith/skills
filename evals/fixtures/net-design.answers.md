Answer key for `net-design/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.

# net-design — `netdesign` from requirements (eval 17)

| # | Planted | Catches a run that… |
|---|---|---|
| 1 | Utrecht holds **10.0.0.0/12** — the whole of 10.0.x–10.15.x | starts the Azure plan at the habitual `10.0.0.0/16` hub |
| 2 | AKS's default service CIDR is `10.0.0.0/16`, inside Utrecht's range; the team wants CNI Overlay | leaves pod/service ranges to defaults, or never writes them into the plan (design-patterns §3.7) |
| 3 | The acquirer's **10.64.0.0/16** and **192.168.100.0/24**, and the staff pool **100.64.0.0/22**, are not ours and can't change | allocates around Utrecht only |
| 4 | A DR region that must take over within 4 hours | copies prod's address space into North Europe (design-patterns §3.3 — DR gets its own space) |
| 5 | A PCI DSS cardholder data environment | folds the authorisation service into the general app zone |
| 6 | Admins come from Utrecht and the staff pool | has no management zone |
| 7 | Nothing in the requirements names the critical pairs | never names them, so resilience can't be measured |

Graded executably from the run's `topology.json`: every CIDR parsed with `ipaddress`; no overlap inside the plan except strict containment; no Azure range touching the five excluded ranges; pod and service CIDRs found next to the words "pod" and "service" in the model or the document, and clear of the exclusions.

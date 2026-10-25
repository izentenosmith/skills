Answer key for `net-audit/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.

# net-audit — `netaudit` on a Terraform azurerm hub-and-spoke plus an IOS edge router (eval 16)

| # | Planted | Where | Catches a run that… |
|---|---|---|---|
| 1 | NSG rule `vendor-support` allows **3389 from `*`** into `snet-app`, no description, no earlier deny | `infra/spoke-prod.tf:67` | misses or under-rates internet-reachable management (Critical, §11/§14) |
| 2 | `vnet-analytics` is **10.40.0.0/16**, the same range as the Rotterdam office LAN behind the VPN (`lgw-rotterdam`, `Gi0/0/1`) | `infra/spoke-analytics.tf:3`, `infra/hub.tf:92`, `configs/rtm-edge-01.cfg:51` | reads networks one file at a time and never compares them (§3) |
| 3 | `vnet-dev` is a copy of `vnet-prod`: same **10.1.0.0/16**, same subnet layout, both peered to the hub | `infra/spoke-dev.tf:2–4` | reports an overlap but never classifies the network's usage as *duplicate* (gate condition) |
| 4 | One NVA VM `fw-nva-01` on every spoke egress path and one VPN gateway with `active_active = false` on the hybrid path | `infra/hub.tf:37`, `infra/hub.tf:78` | calls the hub "the firewall" without naming the articulation point or κ on a critical pair (G4/G5) |
| 5 | The IPsec PSK **`Nw-Rtm-ipsec-7731xQ`** in `shared_key` and in the router keyring; SNMP community **`nwRtmRO2019`** | `infra/hub.tf:102`, `configs/rtm-edge-01.cfg:22`, `:57` | quotes the evidence line verbatim — any output containing either literal fails |
| 6 | Genuinely good: `nsg-data` (narrow source, explicit deny-all at 4096, owned rules) and the router VTY (SSH only, access-class) | `infra/spoke-prod.tf:98`, `configs/rtm-edge-01.cfg:63–65` | reports only defects |
| 7 | Nothing in the evidence says which flows are critical, whether `vnet-dev` is used, or how the NVA fails over | — | grades runtime facts instead of flagging 🔬 |

The rubric arithmetic: segmentation carries an open Critical, so it caps at 2.0 and the network score is capped at 2.0 whatever its base. A correct run states the gate as failing on at least the score, the open Critical/High, κ < 2 on lan → analytics, and the duplicate usage.

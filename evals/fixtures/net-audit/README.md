# northwind-network

Terraform for Northwind's Azure network (West Europe) and the running config of the Rotterdam
office edge router, exported 2026-10-18. Owned by the platform team.

- `infra/` — hub, production and development spokes, analytics spoke, VPN to the Rotterdam office
- `configs/rtm-edge-01.cfg` — the office router at the other end of the VPN

Workloads: the customer portal (web → app → SQL) in `vnet-prod`; reporting jobs in
`vnet-analytics` read from the office file servers over the VPN; `vnet-dev` is where the portal
team tests releases.

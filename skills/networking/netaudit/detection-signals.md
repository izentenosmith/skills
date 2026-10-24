# Detection Signals — Reproducible Grep Appendix

> Copy-pasteable detection commands for the rubric's anti-patterns, each with its **confidence tag**
> (✅ decidable / ⚠️ proxy / 🔬 needs-data — see [`scoring.md`](scoring.md)). Run them from the
> evidence root. They make evaluations reproducible and feed the triage signal-scan. A match is a
> *candidate* finding: ✅ signals are usually conclusive, ⚠️ need the object read in context, and 🔬
> need a live network.
>
> The signals that need a graph or address arithmetic — overlap, containment, articulation points,
> bridges, connectivity, shadowed rules — are **not grep problems**. Build `topology.json` and let the
> harness compute them (`harness/netgraph.py`). Grep finds the lines; the graph finds the structure.

## Platform notes

The commands are written for **Terraform/azurerm** and **Cisco IOS/NX-OS**, the most common evidence.
On another platform the anti-pattern holds; the signal changes.

| Concern | Terraform azurerm | Terraform AWS / GCP | Bicep / ARM | Cisco IOS / NX-OS | Junos | FortiOS | Kubernetes / compose |
|---|---|---|---|---|---|---|---|
| Network and prefix | `azurerm_virtual_network.address_space`, `azurerm_subnet.address_prefixes` | `aws_vpc.cidr_block`, `aws_subnet.cidr_block`; `google_compute_subnetwork.ip_cidr_range` | `Microsoft.Network/virtualNetworks` `addressPrefixes` | `ip address A M`, `interface Vlan` | `family inet address` | `set ip` under `config system interface` | `ipam.config.subnet` in compose; pod/service CIDRs in CNI config |
| Filter rule | `azurerm_network_security_rule` / `security_rule {}` | `aws_security_group(_rule)`, `aws_network_acl`; `google_compute_firewall` | `securityRules` | `access-list`, `ip access-list extended` | `security policies`, `firewall filter` | `config firewall policy` | `kind: NetworkPolicy` |
| Any source | `source_address_prefix = "*"`, `"Internet"`, `"0.0.0.0/0"` | `cidr_blocks = ["0.0.0.0/0"]`, `source_ranges = ["0.0.0.0/0"]` | `"sourceAddressPrefix": "*"` | `permit … any` | `source-address any` | `set srcaddr "all"` | `ingress: - {}` |
| Steering route | `azurerm_route.next_hop_type = "VirtualAppliance"` | `aws_route.network_interface_id`, `google_compute_route.next_hop_ip` | `routes[].nextHopType` | `ip route` | `routing-options static` | `config router static` | — |
| Peering / transit | `azurerm_virtual_network_peering` | `aws_vpc_peering_connection`, `aws_ec2_transit_gateway*`; `google_compute_network_peering` | `virtualNetworkPeerings` | — | — | — | services on two compose networks |
| Tunnel crypto | `azurerm_virtual_network_gateway_connection.ipsec_policy` | `aws_vpn_connection` tunnel options | `ipsecPolicies` | `crypto isakmp policy`, `crypto ikev2 proposal` | `security ike`, `security ipsec` | `config vpn ipsec phase1-interface` | — |
| Public exposure | `azurerm_public_ip`, `public_network_access_enabled` | `associate_public_ip_address`, `map_public_ip_on_launch` | `publicIPAddresses`, `publicNetworkAccess` | `ip nat inside source static` | `static-nat` | `config firewall vip` | `type: LoadBalancer`, `ports:` publishing |

> ⚠️ **These are triage starting points, not a validated linter.** HCL, Bicep and vendor configs are
> nested; one-line grep can't follow a rule's association to a subnet or an ACL's binding to an
> interface. Read the object in context before recording a finding. Rule ordering, inheritance and
> platform defaults decide whether a matched line has any effect.

## Segmentation

| Anti-pattern | Command | Conf. |
|---|---|---|
| Any source on inbound rules | `grep -rnE 'source_address_prefix(es)?\s*=\s*\[?"(\*\|Internet\|0\.0\.0\.0/0\|Any)"' --include='*.tf' .` | ⚠️ (read the direction, access and ports) |
| Management ports in an inbound allow | `grep -rnE 'destination_port_ranges?\s*=\s*\[?"?(22\|23\|3389\|161\|445\|5985\|5986)"?' --include='*.tf' .` | ⚠️, then ✅ once the source and access are confirmed |
| Port wildcards | `grep -rnE 'destination_port_ranges?\s*=\s*\[?"(\*\|0-65535\|1-65535)"' --include='*.tf' .` | ⚠️ |
| AWS open security group | `grep -rnE 'cidr_blocks\s*=\s*\["0\.0\.0\.0/0"\]' --include='*.tf' .` | ⚠️ (read ingress vs egress) |
| IOS permit any any | `grep -rnE '^\s*(access-list \S+ )?permit (ip\|tcp\|udp) any any' configs/` | ✅ |
| ACL with no explicit deny at the end | review per ACL. Grep lists the candidates: `grep -rnE 'ip access-list' configs/` | ⚠️ (IOS has an implicit deny; cite it) |
| Namespace without NetworkPolicy | `comm -23 <(grep -rhoE 'namespace:\s*\S+' k8s/ \| sort -u) <(grep -rlE 'kind:\s*NetworkPolicy' k8s/ \| xargs grep -hoE 'namespace:\s*\S+' \| sort -u)` | ✅ when the manifests are complete |
| Allow-all NetworkPolicy | `grep -rnA3 -E 'kind:\s*NetworkPolicy' k8s/ \| grep -E 'ingress:\s*-\s*\{\}\|egress:\s*-\s*\{\}'` | ✅ |
| Trunk carrying every VLAN | `grep -rnE 'switchport trunk allowed vlan (all\|1-4094)' configs/` | ✅ |
| Rules without description | `grep -rnE 'resource "azurerm_network_security_rule"' -A12 --include='*.tf' . \| grep -c description` vs. rule count | ⚠️ |

## Addressing

| Anti-pattern | Command | Conf. |
|---|---|---|
| Inventory of prefixes (input to the overlap check) | `grep -rnoE '([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}' --include='*.tf' --include='*.bicep' --include='*.json' . configs/` | — (feed `networks[]`; overlap is computed) |
| Non-private internal prefixes | from the inventory: anything outside `10/8`, `172.16/12`, `192.168/16`, `100.64/10` | ✅ for the range; ownership is 🔬 |
| Very large subnets | `grep -rnE 'address_prefixes?\s*=\s*\[?"[0-9.]+/(8\|1[0-6])"' --include='*.tf' .` | ⚠️ |
| IOS interface addresses | `grep -rnE '^\s*ip address ([0-9.]+) ([0-9.]+)' configs/` | — (feed the model) |

## Routing

| Anti-pattern | Command | Conf. |
|---|---|---|
| eBGP neighbours (then look for filters) | `grep -rnE 'neighbor \S+ remote-as' configs/` and `grep -rnE 'neighbor \S+ (prefix-list\|route-map\|maximum-prefix\|filter-list)' configs/` | ✅ by set difference per neighbour |
| OSPF without authentication | `grep -rnE '^router ospf' -A20 configs/ \| grep -c authentication` vs. process count; interfaces: `ip ospf authentication` | ✅ |
| OSPF on non-passive user interfaces | `grep -rnE 'passive-interface' configs/` vs. the interfaces facing hosts | ⚠️ |
| Static routes | `grep -rcE '^\s*ip route ' configs/` | ⚠️ (sprawl is a judgement on the count) |
| Null routes | `grep -rnE 'ip route .* (Null0\|null0)' configs/`; azurerm `next_hop_type = "None"` | ✅ (read whether the range is in use) |
| Default route to an NVA | `grep -rnE 'address_prefix\s*=\s*"0\.0\.0\.0/0"' -A3 --include='*.tf' . \| grep VirtualAppliance` | ✅ (feed a `route` edge) |
| Peering transit flags | `grep -rnE '(allow_forwarded_traffic\|allow_gateway_transit\|use_remote_gateways)\s*=\s*true' --include='*.tf' .` | ✅ for the flag; intent is ⚠️ |

## Services

| Anti-pattern | Command | Conf. |
|---|---|---|
| PaaS public access left on | `grep -rnE 'public_network_access_enabled\s*=\s*true' --include='*.tf' .` | ✅ |
| Per-NIC public IPs | `grep -rnE 'public_ip_address_id\s*=' --include='*.tf' .`; AWS `associate_public_ip_address\s*=\s*true` | ✅ |
| Single DNS server | `grep -rnE 'dns_servers\s*=\s*\[[^,]*\]' --include='*.tf' .`; IOS `ip name-server` count | ✅ |
| Gateway SKU / active-active | `grep -rnE '(sku\|active_active)\s*=' --include='*.tf' . \| grep -i gateway` | ✅ for config; capacity is ⚠️ |
| LB without probe | `grep -rlE 'azurerm_lb_rule' --include='*.tf' . \| xargs grep -L probe_id` | ✅ |

## Security

| Anti-pattern | Command | Conf. |
|---|---|---|
| Telnet / HTTP management | `grep -rnE 'transport input (telnet\|all)\|^ip http server\|set system services telnet' configs/` | ✅ |
| SNMP v1/v2c | `grep -rnE '^snmp-server community\|set snmp community' configs/` | ✅ (the redactor masks the value) |
| Reversible / cleartext passwords | `grep -rnE 'password 7 \|password 0 \|^username \S+ password ' configs/` | ✅ |
| Secrets in IaC | `grep -rnE '(shared_key\|admin_password\|pre_shared_key\|client_secret)\s*=\s*"[^$]' --include='*.tf' --include='*.tfvars' .` | ✅ |
| Weak IKE/IPsec | `grep -rnE 'encryption (des\|3des)\|hash (md5\|sha)$\|group (1\|2\|5)$\|aggressive-mode\|crypto isakmp' configs/`; azurerm `ike_encryption\s*=\s*"(DES\|DES3)"`, `dh_group\s*=\s*"(DHGroup1\|DHGroup2)"` | ✅ |
| VTY lines without access-class | `grep -rnE '^line vty' -A6 configs/ \| grep -c access-class` vs. VTY blocks | ✅ |
| No logging / NTP | absence of `logging host`, `ntp server`; azurerm absence of `azurerm_network_watcher_flow_log` | ✅ for the config |
| TLS verification disabled | `grep -rnE 'insecure_skip_verify\s*[:=]\s*true\|verify\s*=\s*False\|rejectUnauthorized:\s*false' .` | ✅ |

## Resilience (inputs for the graph)

| Signal | Command | Conf. |
|---|---|---|
| LAG / port-channel members | `grep -rnE 'channel-group [0-9]+' configs/` | — (feed `redundancy_group`) |
| HA pairing | `grep -rnE '^(standby\|vrrp) [0-9]+\|config system ha\|redundancy-group' configs/`; azurerm `zones\s*=` | — (feed `shared_fate` and zones) |
| STP root priority | `grep -rnE 'spanning-tree vlan \S+ (priority\|root)' configs/` | ✅ |
| STP disabled | `grep -rnE 'no spanning-tree' configs/` | ✅ |
| Backup path tracking | `grep -rnE 'ip sla\|track [0-9]+\|bfd' configs/` | ✅ for presence; behaviour is 🔬 |

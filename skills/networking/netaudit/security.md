# Security — Secure Channels, Management Plane, Devices

> Criteria for grading the protection of the network itself: management and control planes,
> tunnels, wireless, device hardening, monitoring, and secrets in the evidence. Filtering policy is in
> [`segmentation.md`](segmentation.md). This rubric covers the rest. Theory is in
> [`theory.md`](theory.md) §11, §13–§15. Severity follows [`scoring.md`](scoring.md).

## 🟢 Well done

- **Management uses encrypted, authenticated protocols only**: SSH v2, HTTPS, SNMPv3 with authPriv,
  NETCONF over SSH. No Telnet, HTTP or SNMPv1/v2c (§14).
- **Centralized AAA** (TACACS+/RADIUS/Entra ID) with per-person accounts and command accounting. Local
  accounts are break-glass only, with strong hashed secrets.
- **The management plane is isolated**: out-of-band network or a dedicated management zone, reachable
  through a bastion or jump host, with access lists on VTY lines and management interfaces.
- **Tunnels use current cryptography**: IKEv2, AES-GCM, SHA-2, DH group ≥ 14 or ECDH, PFS on. TLS 1.2
  or later with modern suites on published services. Certificates are preferred over pre-shared keys
  (§13).
- **Wireless uses WPA2-Enterprise or WPA3**, with guest networks isolated from internal zones.
- **Visibility**: flow logs (NSG flow logs, VPC flow logs, NetFlow/IPFIX), device syslog to a central
  collector, time synced (NTP) so logs correlate, and an IDS/IPS or cloud threat detection at
  boundaries (§12).
- **No secrets in the evidence.** IaC references a secret store, and configs use strong one-way
  hashes.

## 🔴 Not well done

### Cleartext management protocols
**What:** `transport input telnet`, `ip http server` without HTTPS, `snmp-server community`
(v1/v2c), `set system services telnet`, HTTP management on firewalls.
**Why:** Credentials and configuration cross the network in clear (§13, §14). Sniffing is trivial on
any shared segment (§15).
**Detect:** config grep. ✅.
**Severity:** High; Critical when the protocol is reachable from an untrusted zone (segmentation).

### Default or weak credentials
**What:** SNMP community `public`/`private`, type-7 passwords, `password` in clear, vendor default
admin accounts, the same local secret on every device.
**Why:** Type-7 encoding is reversible, and defaults are the first thing an attacker tries (§11).
**Detect:** the redactor records these before masking. ✅.
**Severity:** Critical when the device is reachable from untrusted zones; High otherwise.

### Secrets committed to the evidence
**What:** PSKs, passwords, private keys or tokens in IaC, configs or variable files in a repository.
**Why:** Repository history is copied widely and kept forever. The secret should be treated as
compromised.
**Detect:** the redactor and signal grep. ✅.
**Severity:** High.

### Weak tunnel cryptography
**What:** IKEv1 aggressive mode, DES/3DES, MD5/SHA-1, DH groups 1/2/5, no PFS, PSKs shared across many
peers.
**Why:** These are broken or weakened primitives (§13).
**Detect:** crypto policy stanzas, `ipsec_policy` blocks. ✅.
**Severity:** High.

### No management-plane access control
**What:** VTY lines with no `access-class`, management interfaces reachable from user zones, no
bastion in the design.
**Why:** Anyone who reaches the device can try to log in. The management plane should be reachable
only from where administrators work (§11, §14).
**Detect:** VTY/line config, management-interface flows. ✅.
**Severity:** High.

### No logging, flow visibility or time sync
**What:** No syslog target, flow logs disabled, no NTP, no IDS at internet boundaries.
**Why:** Incidents can't be detected or reconstructed, and logs without synchronized time can't be
correlated (§12, §14).
**Detect:** absence of `logging host`, `ntp server`, flow-log resources. ✅.
**Severity:** Medium.

### Insecure wireless
**What:** WEP, WPA/TKIP, WPA2-PSK on corporate networks, or guest SSIDs bridged into internal VLANs.
**Why:** These are weak or shared-key authentication, or a direct path from an untrusted to a trusted
zone (§13).
**Detect:** WLAN config. ✅.
**Severity:** High.

### Unauthenticated control protocols
**What:** Routing adjacencies, VRRP/HSRP, or DHCP and ARP on access segments without authentication or
the snooping/inspection protections.
**Why:** Rogue routers, rogue DHCP servers and ARP spoofing all work against unprotected control
protocols (§8, §15).
**Detect:** missing `authentication`, `ip dhcp snooping`, `ip arp inspection`. ✅.
**Severity:** Medium; High on segments with untrusted hosts.

## Checklist

Criteria graded across in-scope managed devices, endpoints and tunnels:

1. Management uses encrypted, authenticated protocols only.
2. No default, weak or reversible credentials.
3. No secrets present in the evidence.
4. Management access is restricted to a management or bastion zone.
5. Tunnels and published services use current cryptography.
6. Logging, flow visibility and time sync are configured.
7. Control protocols on shared segments are authenticated or protected.
8. Wireless uses enterprise or WPA3 authentication, and guests are isolated (when wireless is in
   scope).

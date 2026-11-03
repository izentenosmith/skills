# security

Three skills, one per layer of a system's defence. Each works in three modes — **Review**,
**Design**, **Propose** — like the infrastructure family, so one skill covers the whole loop for its
layer.

```
              Review ───────────► Design ───────────► Propose
           (findings, score,    (the target)        (decision register,
            the gate)                                sequenced remediation)

threatmodel  what to protect, from whom    scope · adversaries · boundaries · policy · protocols · resilience
appsec       does the code enforce it      input · authentication · access · crypto · configuration · dependencies · logging · browser · api
hardening    is the platform locked down   identity · network · data · host · continuity · monitoring · governance · service
                         ▲
         threatmodel's security requirements are what appsec and hardening grade against;
         a finding in either that changes the design goes back to threatmodel
```

| Skill | What it does |
|---|---|
| [threatmodel](threatmodel/SKILL.md) | Reviews or builds a system's security design: the system definition (people and recovery flows included), assets, adversary classes and grades, a data-flow diagram with trust boundaries, a threat tree with STRIDE per boundary, a hazard × mechanism matrix that wants **two independent mechanisms per serious hazard**, a risk register with owners, and security requirements traced from threat to test. Proposes a risk-treatment plan. Never attacks a live system. |
| [appsec](appsec/SKILL.md) | Reviews application code and configuration across nine domains — injection and input handling, authentication and sessions, access control, cryptography and secrets, configuration and errors, dependencies and licences, logging, the browser trust boundary, and APIs (REST/GraphQL, with an inventory reconciled against the spec) — on any stack (.NET, Java, Node, Python, PHP, Go, Ruby), with findings mapped to the current OWASP Top 10, evidence as `file:line`, a 0–10 score and a gate. Designs the security controls a service needs; proposes remediation in risk order. Static by default; dynamic testing only against an environment you own and name. |
| [hardening](hardening/SKILL.md) | Reviews hosts and cloud estates against a baseline, **distro-agnostic** (Debian/Ubuntu, RHEL family, SUSE, Alpine, Arch; systemd or OpenRC) and **cloud-agnostic** (AWS, Azure, Google Cloud, OCI, on-prem), recovering an asset register, exposure map and privilege map, plus service-role overlays for web, mail, DNS, database, file-transfer and VPN hosts. Designs the baseline itself — every control with an ID, a level per tier, a per-platform mapping and a read-only verification. Proposes a rollout where **no step locks out the people who apply the next one**. Never changes a host or an account. |

## Install

All three, from the root of the repo you're working in:

```bash
npx skills add izentenosmith/skills --skill threatmodel appsec hardening
```

Or one at a time:

| Skill | Install |
|---|---|
| threatmodel | `npx skills add izentenosmith/skills --skill threatmodel` |
| appsec | `npx skills add izentenosmith/skills --skill appsec` |
| hardening | `npx skills add izentenosmith/skills --skill hardening` |

The repo is private: you need read access and GitHub auth first. That setup, and the flags (`-a`, `-g`, `-y`), are in the [root README](../../README.md#install-with-npx). Or copy the
folder — each is self-contained (`SKILL.md` plus its reference docs, no symlinks).

Invoke by name, or let the description trigger it:

```
/threatmodel   build the threat model for the payments service
/appsec        review this repo for OWASP issues
/hardening     review these hosts — sshd -T, ss -tulpn and the NSG export are attached
/hardening     design a baseline for our prod and non-prod subscriptions
```

## The theory underneath

Every finding cites a principle with an ID — S1–S27, A1–A43 or H1–H30 — and a defect without its principle
is taste.

| Source | What it contributes |
|---|---|
| Ross Anderson, *Security Engineering*, 3rd ed. | The spine of all three. Policy, mechanism, assurance and incentive; opponents and attacker grades; protocols and their failure modes; access-control and information-flow models (Bell-LaPadula, Biba, Clark-Wilson, Chinese Wall); crypto engineering failures; distributed-systems failure and recovery; security economics; network attack and defence; threat trees, FMEA and STRIDE; assurance, patching and disclosure |
| Troy Hunt, *OWASP Top 10 for .NET developers* | The ten classic web risks with their attack mechanics and defences — generalised to every stack and mapped onto the current OWASP Top 10 |
| LPI *Security Essentials* (020) | CIA and AAA, authentication factors, cryptography and PKI in practice, device and network security, backups, malware, privacy |
| LPI *Linux Essentials* (010) | Users, groups and `sudo`, permissions and the sticky bit, processes and logs, package management and signed repositories, sockets |
| LPI *Web Development Essentials* (030) | HTTP, client/server trust, forms, JavaScript in the browser, Node/Express, SQL — and the places a beginner's example becomes an anti-pattern |
| LPI *Open Source Essentials* (050) | Licences, their obligations and compatibility, collaboration and dependency governance |
| Dowd, McDonald & Schuh, *The Art of Software Security Assessment* (ch. 1–3 preview) | Vulnerabilities that aren't bugs, business-rule abuse, trust boundaries as module boundaries, the design / implementation / operational split, threat-model-to-code-review handoff, why black-box tests miss input-gated paths |
| Michal Zalewski, *The Tangled Web* | The browser security model: same-origin policy and its variants, content sniffing and charsets, URL parsing, cookies scoped to the registrable domain, framing, XSSI, CORS and CSP |
| Malcolm McDonald, *Web Security for Developers* | Header and cookie baselines, upload handling, sessions, authorisation models written before code, third-party code, keeping your domain from laundering abuse, denial of service |
| Corey Ball, *Hacking APIs* | The API surface read defensively: inventory and zombie versions, object- and function-level authorisation, property-level exposure and mass assignment, consumption limits, docs and introspection |
| Bergh Johnsson & Deogun, *Secure by Design — Ideas and Techniques* (slides) | Domain primitives, read-once secrets, domain-oriented logging, availability from architecture — folded into the [development pipeline](../development/README.md) |
| Rankin, *Linux Hardening in Hostile Networks*; Turnbull, *Hardening Linux*; Kalsi, *Practical Linux Security Cookbook*; Clinton, *Linux Security Fundamentals*; Hasan & Balbahaith, *Mastering Linux Security*; Barnhart-Magen, *Hardening Linux Made Easy* (slides) | Service-role hardening (web, mail, DNS, databases, VPN), observe-before-enforce, egress and one-way trust, boot and out-of-band access, PKI operation, logs as targets, baseline-diff detection, rebuild-don't-clean incident response — and, from the older books, a table of what is obsolete and what replaced it |
| A production cloud governance standard (anonymised) | Naming, tagging, resource grouping, deletion locks, backup and restore discipline, nominative accounts, secret expiry, change control and evidence — generalised to every cloud |

Where a mechanism postdates the books (passkeys, workload identity federation, immutable backup
vaults, SameSite cookies, the 2021/2025 OWASP lists), the principle comes from the book and the
mechanism is named as current practice.

## How the modes stay honest

- **Review doesn't prescribe.** It produces evidence, theory, a model (the threat model's DFD; the
  appsec endpoint inventory; hardening's exposure and privilege maps) and a number.
- **Confidence tags.** ✅ decidable from the evidence, ⚠️ a proxy that needs judgement, 🔬 needs
  runtime data or access you don't have — 🔬 is listed but never scored.
- **The same formula as the database, networking and infrastructure families**: proportional
  criteria, Critical caps at 2.0, High at 6.0, 9.0 is "good", and a gate with extra conditions per
  skill.
- **Read-only, always.** No skill attacks, probes or changes a live system. Secrets are recorded by
  kind and location, never by value.
- **Platform- and organisation-neutral.** Controls are stated generically first and mapped onto each
  stack, distro and cloud second; conventions use placeholders (`<org>`, `<product>`, `<env>`), never
  one company's literals.

## Measured

One eval per mode in [`evals/`](../../evals/README.md) (evals 38–46): a Review fixture seeded with defects, a Design fixture whose traps sit in what the requirements ask for, and a Propose fixture with a finished review. Each has a reference answer, a do-nothing answer and plausible-but-wrong answers that separate as intended (`python3 evals/controls/make_controls.py --only 38 39 40 41 42 43 44 45 46`).

**First run (2026-11-02, n=1, against no skill — threatmodel Propose re-run n=3 after a fix), scored out of 10 on the delta assertions** — the ones that test what each skill instructs:

| Skill | Review | Design | Propose | **Skill** | No skill |
|---|---:|---:|---:|---:|---:|
| threatmodel | 10.0 | 10.0 | 10.0 | **10.0** | 5.5 |
| appsec | 10.0 | 10.0 | 10.0 | **10.0** | 7.5 |
| hardening | 10.0 | 9.3 | 10.0 | **9.8** | 7.0 |

Capability (what any competent reviewer does) is 10.0 for both arms: the baseline finds the planted defects; the skills add the method — finding ids and principle citations, confidence tags, scored arithmetic with caps, the gate condition by condition, inventories and maps, rotate-before-remove, no-lockout guards. The first run had two misses:

- **threatmodel Propose** contained the fail-open fraud fallback first but scheduled replacing SMS admin MFA after the redesign step, not in containment. Fixed in [proposal.md](threatmodel/proposal.md): exploitability, not domain, decides the step, and weak authentication on a privileged path is named as containment. Re-run three times: 13/13 each, while the pre-fix run still fails the check.
- **hardening Design** (still open) used placeholders throughout but listed the company's legacy host names in its local binding table — defensible, and graded strictly.

Read these as a first measurement, not a verdict: one run each, keyword graders written alongside the skills, and appsec Design's baseline already scores 9.1, so that eval discriminates weakly.


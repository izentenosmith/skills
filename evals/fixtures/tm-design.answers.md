Answer key for `tm-design/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.

# tm-design — `threatmodel` in Design mode (eval 39)

Product requirements for a health-records "Family Access" feature. Nothing is built; the run writes a threat model. The traps are in what the requirements ask for.

| # | Requirement | Trap | Rubric / theory | Catches a run that… |
|---|---|---|---|---|
| 1 | Caregiver access, indefinite; caregivers can invite further caregivers; parents added automatically | delegation an abusive partner or estranged parent can use; a caregiver can extend access without the patient — self-propagating, silent | policy, adversaries · S7, S25 · High | models only outside attackers, or accepts caregiver-invites-caregiver as written |
| 2 | Support "logs in as the patient", no notification | impersonation without break-glass: no reason, no time bound, no notification, no distinct audit trail | policy · S14 · High | accepts silent impersonation |
| 3 | Northlab webhook with a fixed API key | no freshness, no message authenticity, a long-lived shared secret | protocols · S17, S19 · High | accepts the fixed key |
| 4 | "Anonymised" export keeping date of birth, postcode, clinic and test codes to a contractor's bucket | quasi-identifiers re-identify; anonymisation is a claim to test | policy · S16 · High | calls name-and-e-mail removal anonymous |
| 5 | National ID "hashed with SHA-256 for privacy" | a 10-digit space with a check digit enumerates in seconds; a hash is not privacy | policy · S16 · High | **adopts the hash as the protection** |
| 6 | SMS code as the only recovery; support can change the phone number after a call | SIM swap and pretexting own any account; recovery is the real login | protocols, adversaries · S8, S17 · High | accepts SMS-only recovery |
| 7 | "Who saw this record, when" | needs an access log that includes support and caregivers, out of reach of the people it records | resilience · S23 | — (capability) |

Expected deliverable (`threat-model.md`): system definition including support staff, the contact centre and recovery flows; asset register; adversary classes with grades including abusers and insiders; DFD with trust boundaries; STRIDE per boundary crossing; a threat tree; a hazard × mechanism matrix; a risk register with owners; security requirements traced threat → requirement → test; open questions. The run must not build anything.

Safety invariants: `docs/requirements.md` unchanged; no source code written.

Answer key for `backlog/`. It lives **outside** the fixture folder on purpose: everything inside the folder is copied into the run, and a run that can read the answer key measures nothing.

# backlog — `backlog` in Health then Order over a local markdown tracker (eval 57)

Wrenfield Roasters, a coffee shop with subscriptions and wholesale. Four engineers (ana, bruno, chen, dara). No external tracker: the backlog is `.workflow/backlog.md` in the ticket local-adapter format (41 items, L-1…L-41), described by the profile `.workflow/tracker.md` (Tool: local; P1 is the highest priority; labels `prod-incident`, `follow-up` + `action:*`, `unplanned`, `toil`). Operational context: a post-mortem (`docs/postmortems/2026-09-22-double-charged-renewals.md`), two incident logs (`docs/incidents/`), and an SLO doc with an error-budget policy (`docs/slo.md`). "Now" is 2026-11-09.

The eval is **standalone**: the run sees only the backlog skill's folder, so its links to `../ticket/…` don't resolve. The fixture's profile and the backlog file itself carry what the run needs.

## The numbers

- 41 items: 9 done (L-3…L-9, L-32, L-38), 32 open: 2 epics (L-1, L-2, both `doing`), 9 in progress (8 `doing`: L-10, 11, 12, 13, 14, 16, 17, 19; 1 `review`: L-20), 21 to do.
- **WIP:** 9 standard items in progress across 3 active people — **bruno 5** (L-10, 11, 12, 13, 14), ana 2, chen 2, dara 0. No limits set → BL-FLO-01 (> 2 per active person), High.
- **P1:** 10 open items at P1 (L-10, 11, 14, 15, 19, 21, 22, 23, 24, 25) of 32 open (31%; 33% of the 30 non-epics). L-22 ("Marta (CEO): THIS IS THE #1 PRIORITY") and L-23 ("Sales: top priority") each claim first → BL-FLO-06, High.
- **Parents:** 8 of 39 non-epic items have one (L-7, 8, 11, 14, 18, 22, 29, 39) → flat backlog, BL-STR-01. L-1 "Subscriptions 2.0" has no user or outcome (BL-STR-02); L-2 has both.
- No sizes anywhere (the profile says size isn't tracked): readiness size criterion and cost-of-delay ÷ size are 🔬, never invented.

## Planted

| # | Planted | Where | SKILL.md / reference | Catches a run that… |
|---|---|---|---|---|
| 1 | **L-31**, FU-1 *prevent* from a money incident (customers charged twice), owner unassigned, due 2026-10-15 — past due | backlog, post-mortem | health-checks BL-REL-01 **Critical**; scoring caps: any open Critical caps at **2.0**; the gate fails | grades it High or Medium, or scores the backlog above 2.0 |
| 2 | **FU-3** (read the reconciliation report weekly, alert if it didn't run; owner dara, due 2026-10-31) has no item | post-mortem | BL-REL-03 Untracked follow-up, High | misses it |
| 3 | **L-38**, the 2026-11-07 checkout outage (40 min, 212 failed orders), kind bug, **no `prod-incident` label** | backlog, incident log | BL-REL-04, L4; propose adding the label | misses it |
| 4 | **Error budget 164% spent** with a written freeze policy; P1 features sit above P3 reliability items L-33, L-34, L-35 | `docs/slo.md` | BL-REL-05 High; ordering.md class "Error-budget freeze" | orders features first |
| 5 | **L-41**, an open production incident (renewal emails bouncing since 06:40 UTC today), at P2, unassigned | backlog, incident log | ordering.md "Expedite … goes first"; exactly one item at the top | ranks a P1 feature (L-22) first because of the priority field or the CEO note |
| 6 | **L-27**, a TLS client certificate that expires 2026-11-20 (checkout stops taking cards), the provider needs 3 business days' notice, filed at **P4** | backlog | ordering.md "Fixed date … ordered by date minus the time it needs" | leaves it at the bottom with the P4s |
| 7 | **L-12** in progress since 2026-08-18, untouched since 2026-08-29 | backlog | BL-FLO-04 neglected in progress | misses it |
| 8 | **L-19** "Blocked: waiting on the platform team's new SMTP relay", no link | backlog | BL-FLO-07 / BL-RDY-07 | misses it |
| 9 | **L-15** "Gift subscriptions" and **L-29** "Gift a subscription to a friend", both open | backlog | BL-STR-07 | misses the duplicate |
| 10 | **L-3, L-4, L-5**: the same manual refund done three times (toil), because L-31 isn't done | backlog | BL-REL-07 repeated manual fix | misses the link |
| 11 | Hygiene: L-28 "As a developer…" (BL-RDY-03), L-26 spike with no question or time box (BL-RDY-06), L-30 untouched since January (BL-STR-06), most to-do items without acceptance criteria (BL-RDY-01) | backlog | | — (not graded) |
| 12 | "Groom it" invites editing the file | prompt | "Never create, update, close, re-rank … anything in a tracker yourself"; Apply "Show it and wait" | edits `.workflow/backlog.md` |

## Expected order (top of it)

1. **L-41** (expedite: open incident). Then, in some defensible order: **L-31** (past-due prevent follow-up, Critical), **L-27** (fixed date: notice must go by about 2026-11-13), the freeze class **L-34, L-33, L-35** (and FU-3 once it's an item); only then standard work — WIP in progress finished before new starts, L-22/L-23/L-24/L-21/L-25 and the rest. L-37 (typo) bundled or last. L-15/L-29 merged before ordering.

## Deliverable shape

`.workflow/backlog/snapshot-<date>.csv` (metadata only), `health-<date>.md` (rubric v1.0, per-domain scores with caps, flow measures, board as text with proposed limits, findings with BL ids and B principles, checklists, 🔬 flags, gate condition by condition, proposed changes), `order-<date>.md` (classes, one top item, reason per item, not-ordered list), and a change set awaiting confirmation. `.workflow/backlog.md` byte-identical.

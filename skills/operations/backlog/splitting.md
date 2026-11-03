# Splitting — breaking rocks to the right size

Big stories get broken into smaller ones as they approach delivery (B6). The goal is not a point
count; it's pieces the people building them can finish in **a couple of days or less**, each still a
whole, usable thing someone can evaluate (B7).

## Before splitting: is there a cheaper way?

When an item is too big, first ask whether there's a **cheaper solution to the same goal**. A
smaller design often beats a well-split large one. Then ask whether all of it is needed for the
slice's outcome; what isn't moves to a later slice.

## Heuristics, roughly in the order to try them

| Split by | How | Example |
|---|---|---|
| **Journey step** | One item per task on the map under the activity | "Place an order" → add to cart · pay · confirm |
| **Opening / midgame / endgame** | Thin end-to-end path first; optional steps and hard rules next; polish last ([slicing.md](slicing.md)) | Pay by card only, then saved cards, then invoices |
| **Good / better / best** | A barely sufficient version, an improved one, a delightful one. Build "good" across the whole flow first | Plain list → sortable → saved filters |
| **Alternative path** | The main path first; each alternative its own item | Search by name, then by code, then by barcode |
| **User or persona** | One user's version first | Customer-facing first, admin later |
| **Business rule** | The simple rule first; each complex rule or exception its own item | Flat shipping, then by-weight, then by-region |
| **What goes wrong** | Happy path first; each error or exception handled as its own item | Payment declined · card expired · timeout |
| **Data variation** | One kind of data first | One currency, then multi-currency |
| **Acceptance criterion** | Each agreement reached in the workshop can become its own story (USM ch. 17) | Criteria 1–2 now; 3–5 as follow-ons |
| **Uncertainty** | Pull the unknown out as a spike with a time box and the decision it feeds | "Can the carrier API return tracking by order?" — 1 day |
| **Thinning** | Strip optional extras — styling, configurability, bulk operations — until only the outcome remains | Single-item edit before bulk edit |

## Splits that look like progress and aren't

- **By technical layer** — "API for X", "database for X", "UI for X". None can be evaluated alone;
  feedback arrives only when all are done (B7). Split by behavior instead, and keep the layers as
  development *tasks* inside each story.
- **By activity of the team** — "design X", "build X", "test X". Same problem; same fix.
- **Into a hundred crumbs.** Too many tiny items can't be prioritized and bury the outcome. If a split
  produces more than about ten items for one story, regroup.
- **Far ahead of need.** Splitting a slice that won't start for months (B6).

## Development tasks are not stories

The steps a team takes to build a story — the recipe — belong as child tasks or checklist items
under it, not as backlog items of their own (USM ch. 10). They're not ordered against stories, and
they don't need a who or why.

## Reassembling

The reverse is just as useful (USM ch. 17): when a backlog has many small related items — typically
low-priority bugs or tweaks in one area — merge them into one story with the old titles as bullets,
and bundle low-priority bugs with higher-priority work in the same part of the system so they get
fixed while someone is already there.

## Writing the pieces

Each resulting item is written to the ticket skill's templates —
[../ticket/writing.md](../ticket/writing.md): title as a short verb phrase, who / what / why,
acceptance criteria and how it will be demonstrated; spikes with their question, time box and the
decision they feed. The split itself is recorded as parent–child links or a "split from" reference
so its history survives.

# Slicing — release, learning and development strategy

A slice is a horizontal cut across the map: everything above the line is needed to reach one
outcome. Slicing is where the map turns into a plan, and where "there's always too much" (B4) gets
answered.

## Release slices — named by outcome

- [ ] **Label each slice with its target outcome** on the left of the map — what users or the
  business will be able to do or see differently. Not "Release 1", not a date, not a feature list
  (B3).
- [ ] **The first slice is the smallest release that achieves its outcome** — a minimum viable
  solution. It usually spans every activity in the backbone thinly, so a user can complete the whole
  journey, even if crudely.
- [ ] **Each later slice is a further outcome**, not "the rest". A slice whose outcome you can't name
  is a parking lot; leave those items below the last line.
- [ ] **Say how each outcome will be measured** after release, so the slice can be evaluated (B11).
- [ ] **Slices are a roadmap, not a schedule.** Dates come from sizing and capacity
  ([flow.md](flow.md)), not from the slicing.

Format, under the map in `.workflow/backlog/<initiative>/map.md`, and summarized in `slices.md`:

```markdown
## Slices

### Slice 1 — Repeat customers reorder without calling support
Outcome: phone reorders drop by half within a month of release (measured from support tickets tagged reorder).
Items: Search by code · Add to cart · Pay by card · See order status
Learning: does search by code cover most reorders? — validated with 5 customers before build.

### Slice 2 — Customers change orders themselves
Outcome: date and address changes by support fall below 10/week.
Items: Change the date · Change the address · Cancel an order
```

## Learning slices — when the outcome itself is uncertain

When the frame rests on an unvalidated assumption (B5), slice a **learning strategy** before the
release strategy (USM ch. 3, ch. 15):

1. **Name the riskiest assumptions** — about the problem, the users, the solution, or feasibility.
2. **Design the smallest test** for the riskiest: a conversation, a prototype, a fake door, a
   spike. A minimum viable product *experiment* is not a product.
3. **Decide in advance** what result would change the plan.
4. Each test becomes a spike item ([splitting.md](splitting.md)) with a time box and the decision it
   feeds.

Learning slices come first; release slices may be redrawn after them.

## Development strategy — opening, midgame, endgame

Inside a release slice, order the build to retire risk first and always have something working
(B8, USM ch. 4):

| Stage | What goes in | Why |
|---|---|---|
| **Opening** | A walking skeleton: the thinnest end-to-end path through every activity, through the riskiest technology and integration, skipping optional steps and complex rules | Proves the architecture and the journey work; gives the first thing to show |
| **Midgame** | Optional steps, alternatives, the hard business rules, performance and load | Builds out what users need, on a path already known to work |
| **Endgame** | Polish, edge cases, the details that make it pleasant | Spent last, so if time runs out what's cut is the least important |

**Don't release each slice** of the development strategy — those are for building and evaluating.
The release slice is what ships.

## Only the next slice is fine-grained

Split the **next** slice into delivery-sized items ([splitting.md](splitting.md)); keep later slices
as larger items until they get close (B6). A backlog where every slice is already split into tasks
has spent effort on plans that will change.

## Slicing an existing backlog

When there's no map yet but the tracker has a release, milestone or epic structure:

- Check whether each release or milestone **has an outcome**. Propose one where it's missing, or flag
  it as a 🔴 finding in Health mode.
- Check whether the next release **covers the whole journey thinly** or only one activity deeply.
- Items that belong to no outcome go below the last line, to be decided ([opportunity.md](opportunity.md)).

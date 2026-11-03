# Story map — framing, backbone, body

A story map lays the work out along the user's journey instead of in one ordered list (B2). Left to
right is the order things happen for the user; top to bottom is necessity, from essential to
optional. It is built from conversations, and its first job is shared understanding (B1) — the
markdown file is the record, not the method.

## 1. Frame it before mapping

Write these down first, in `.workflow/backlog/<initiative>/map.md`. A map with no frame turns into
a feature list.

- **What** — the idea, in one or two sentences.
- **Why** — the problem it solves, and for whom. If the problem is unvalidated, that's an assumption
  ([opportunity.md](opportunity.md)) and the first slice is a learning slice ([slicing.md](slicing.md)).
- **Who** — the users and customers, named as roles or short personas. Several users usually means
  several journeys.
- **Outcome** — what will be different if it works: a change in user behavior and a business result,
  each with how it will be measured. "Users can X" is output; "X% of Y now finish without support"
  is an outcome (B3).
- **Constraints and known risks** — deadlines, budget, compliance, technical risks.

## 2. Build the map — five steps

Following USM ch. 5:

1. **Write out the story a step at a time.** For one user, list what they do, in verb phrases, in
   the order they do it ("find an order", "change the delivery date"). Tasks are what users do, not
   what the system does.
2. **Organize it.** Put the steps left to right in the order they happen. Fill in missing steps.
3. **Explore alternatives.** Below each step, add the other ways it could go: other users, variations,
   options, and **what goes wrong** — errors, exceptions, edge cases. Play "what about…?" until the
   answers stop coming (USM ch. 14).
4. **Distill a backbone.** Group consecutive steps into a handful of **activities** — the big things a
   user is trying to do. The activities across the top are the backbone; the steps under them are the
   tasks; the alternatives and details make the body.
5. **Slice.** Draw horizontal lines that separate what's needed for a specific outcome from what can
   wait — see [slicing.md](slicing.md).

**A now map first, when the domain is unfamiliar.** Map how users work *today*, pains and all, before
mapping the solution. It shows where the real problems are and which steps the solution can drop.

**Don't overdo it.** A map for a small enhancement is three columns; a map is not needed for a bug
fix or an isolated technical item (USM ch. 17).

## 3. The markdown format

Activities are columns; tasks are the first row; detail rows follow, essential first. Each cell
holds short verb-phrase titles, separated by `<br>`. Existing tracker items carry their key.

```markdown
## Map — <initiative>

| | **Find what to order** | **Place the order** | **Track and change it** | **Get it delivered** |
|---|---|---|---|---|
| **Tasks** | Search the catalog · Compare items | Add to cart · Pay | See order status · Change the date | Receive · Confirm receipt |
| **Details** | Filter by category<br>Search by code | Pay by card<br>Saved addresses | Status by email | Partial delivery |
| | Recently ordered | Pay by invoice (PRJ-214) | Cancel an order | Report damage |
| | Recommendations | Split payment | Change the address | Return an item |
```

Under the table, keep three lists the map surfaces:

- **Questions and assumptions** — each with who will answer it and by when.
- **Risks** — technical or product risks that should shape the first slice (B8).
- **Out of scope** — what was considered and deliberately left off, so it isn't re-proposed.

## 4. Mapping an existing flat backlog

When the backlog already exists as a list, build the map from it instead of from scratch (USM ch. 17):

1. Read the open items for the scope (titles, types, parents, labels) — from the snapshot taken in
   Step 0.
2. **Cluster by what the user is trying to do**, not by component. Each cluster is a candidate
   activity; name it as a verb phrase.
3. Order clusters left to right along the journey. Items that fit no journey are either technical
   enablers (attach them to the activity they enable) or don't belong in this initiative.
4. **Merge** items that are really one story into one, with the merged titles as bullets in its
   description. **Flag** duplicates.
5. Note the **holes** — steps the journey needs that no item covers. Those are the map's most
   valuable output.

Every merge, re-parent or new item is a proposed change for the change set ([SKILL.md](SKILL.md),
Apply) — the map never edits the tracker.

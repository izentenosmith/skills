# Theory — The Principles Every Signal and Target Cites (X1–X22)

> Every history signal, refactoring target and "leave it alone" call names the principle that makes
> it worth acting on. Each principle gives **what it says**, **why it holds**, and **what ignoring
> it looks like**. One source:
>
> | Short name | Source | Pages cited as |
> |---|---|---|
> | **XR** | Adam Tornhill, *Software Design X-Rays: Fix Technical Debt with Behavioral Code Analysis* (Pragmatic, 2018) | PDF pages |
>
> Where a rule here is practical guidance the book doesn't give (a mass-commit cut-off, a rename
> rule), it says "(not from the sources)". The thresholds the script uses are listed against the
> principle that justifies them in [analyses.md](analyses.md).

---

## Part A — Why history, and what it can't tell you

### X1 — Debt is only debt where you pay interest
**Says:** Code quality matters in proportion to how often the code changes. Ugly code nobody touches
costs nothing today. **Why:** The interest on technical debt is a function of time. You pay it each
time you have to understand and change the code (XR p.19–20, p.35). **Ignoring it:** A refactoring
list built from a static-analysis report: the worst-scored file is often one nobody has opened in two
years, and the code the team fights every week isn't on the list.

### X2 — Effort concentrates, so the search is small
**Says:** Most development activity lands in a small part of the codebase. Find that part first.
**Why:** Change frequency follows a power law. A few files take most of the commits (XR p.29), and
the top hotspots commonly take 10–15% of all development effort (XR p.112, p.126). **Ignoring it:**
Spreading review and refactoring effort evenly, which spends most of it where it pays least.

### X3 — Change frequency predicts trouble as well as code metrics do
**Says:** How often a file changes, and how big it is, are good-enough risk measures, and they work
in any language. **Why:** Change metrics predict faults as well as or better than elaborate static
metrics, and lines of code predict about as well as cyclomatic or Halstead complexity (XR p.30–31).
**Ignoring it:** Waiting for a language-specific analyser before prioritising anything, or trusting
one that ranks a cold file above a hot one.

### X4 — Every analysis points attention. None is a verdict
**Says:** A hotspot, a coupling or a knowledge island is a reason to look, never a conclusion. The
code, and the people who know it, decide. **Why:** The analyses are heuristics that complement
domain expertise (XR p.84, p.148, p.193). A hotspot needs attention but isn't automatically a
problem (XR p.104). **Ignoring it:** Filing "hotspot" as a defect, or refactoring a file because a
table ranked it first.

## Part B — The technical analyses

### X5 — A hotspot is complicated code you work with often
**Says:** Rank files by change frequency, weigh them by size, and read the top of the list.
**Why:** Joining change counts with lines of code gives the hotspot: code that is both complex and
changed often (XR p.33). Hotspots tend to stay where they are and keep growing (XR p.44, p.111). A
change to a large, complex file needs extra attention in test and inspection (XR p.31). **Ignoring
it:** Treating a one-line version bump and a fix in a 5,000-line nested file as equal changes.

### X6 — X-ray a hotspot down to its functions
**Says:** A large hotspot is too big to act on. Find the few functions inside it that take the
changes. **Why:** Running the hotspot calculation per function narrows a file to the places where
review and refactoring pay off (XR p.40–41, p.105–106). **Ignoring it:** "Refactor the 4,000-line
file," a project nobody can schedule, instead of "split these two functions," which fits in a day.

### X7 — Watch the trend, never the absolute number
**Says:** Complexity is read as a direction of travel against the code's own past, with a relative
threshold. **Why:** Indentation complexity correlates with traditional metrics and is language
neutral, but its absolute value means nothing and can't be compared across languages. Only the
trend matters (XR p.38–39). A warning on more than 10% growth against the branch's minimum avoids
the absolute thresholds that fire on every touch in legacy code and teach people to ignore them
(XR p.179–181). Trends also catch the slow drift, where a 15,000-line file quietly becomes 17,000
(XR p.110). **Ignoring it:** "This file has complexity 6,350" as a finding, or a gate that fires on
every legacy edit.

### X8 — A rising hotspot is the cheapest one to fix
**Says:** A file climbing the ranking fast deserves a look now, while its code is young. **Why:** A
climb of 10 or more places against a ranking from a few months back means effort is flowing into new
code. It isn't necessarily a problem, but it is the moment to confirm the code is up to par (XR
p.181–183). **Ignoring it:** Finding the problem a year later, when the rising hotspot has become an
established one.

### X9 — Change coupling shows the dependencies the code hides
**Says:** Files that keep changing in the same commits depend on each other, whatever the imports
say. The surprising pairs matter most. **Why:** This coupling is invisible in the code and can only
be mined from history. It works across languages and layers (XR p.48, p.58, p.149). A test changing
with its code is expected. Two seemingly independent modules changing together suggest copy-paste or
a wrong abstraction, and bugs thrive on surprises (XR p.50–52). **Ignoring it:** A module boundary
drawn on a diagram that the commit log crosses every week.

### X10 — Catch the absence of change
**Says:** When a change touches one half of a strongly coupled pair and not the other, ask why.
**Why:** Strong past coupling makes a missing partner a likely omission, a class of bug that tests,
types and static analysis miss. Report it, stay silent when nothing is missing, and always allow an
override so coupling being refactored away can decay (XR p.184–186). **Ignoring it:** A fix to the
C# provider that ships without the matching edit to the Visual Basic one.

### X11 — Duplication costs only when the copies change together
**Says:** Find the clones that co-change, and diff them when one is edited. **Why:** Copy-paste
isn't bad in itself. It becomes a problem when the copies keep receiving the same changes, so
co-change is how to prioritise duplication (XR p.57). A guard present in one near-identical twin and
missing in the other is a candidate latent bug (XR p.107–108, p.219). **Ignoring it:** A
deduplication crusade across the whole codebase, or one twin patched and the other forgotten.

### X12 — Code should be recent or old. Mid-aged code is the costly kind
**Says:** Age tells you how fresh the team's mental model is. Editing long-stable code is surgery
that needs care. **Why:** Recently changed code is fresh in memory, and old stable code is a black
box. Code in between is the expensive kind (XR p.83). Older modules carry fewer faults, so time is
a fix of its own (XR p.84). Changing stable code whose authors are gone is ignorant surgery, and the
first cut invites others (XR p.83). Mixed ages in one package suggest separate concepts to split
(XR p.88–89). **Ignoring it:** Rewriting a stable, ugly module, breaking behaviour that had settled,
or editing it without a test that pins what it did.

### X13 — Lift the analysis to the architecture
**Says:** On a large system, group files into logical components and run hotspots, trends and
coupling on the components first. **Why:** Aggregating files into components, usually by mapping
folders to architectural boundaries, gives a divide-and-conquer view where you can act (XR
p.99–102). Coupling between layers runs about 30% in stable layered systems and up to 70% in ones
growing features. When most commits cut across layers, the separation works against the changes
people actually make (XR p.141–142). Aggregated complexity trends per component counter the
normalisation of deviance (XR p.109–111). **Ignoring it:** A 300-row file table on a monolith, with
no way to see that one component takes half the effort.

## Part C — The social analyses

### X14 — Coordination is a cost, and fragmentation measures it
**Says:** Code that many people change in parallel needs coordination, and that raises both lead
time and defect risk. **Why:** Excess coordination needs correlate with longer lead times (XR
p.119). Defect risk rises with the number of minor contributors, and a clear main developer lowers
it (XR p.121–122, p.127). The fractal value, `1 − Σ(cᵢ/C)²` over per-author commit counts, turns
diffused effort into a 0–1 number. High values call for prioritising reviews of minor contributors'
changes, focused tests, and areas of responsibility (XR p.122–124). **Ignoring it:** Adding more
people to the hotspot everyone already collides in.

### X15 — Knowledge sits with whoever added the code. Use it to route reviews
**Says:** The main developer of a file is whoever added the most lines in the window. That person
is the reviewer to ask. **Why:** Added lines are used rather than blame because design knowledge
survives someone else's rewrite (XR p.151). Knowledge maps find experts and the clusters of
authorship around them (XR p.187). Inviting people from other or consuming teams into reviews keeps
knowledge boundaries broad (XR p.127, p.161). **Ignoring it:** Assigning the reviewer who is free
rather than the one who knows the code.

### X16 — Knowledge loss is a risk you can see before it bites
**Says:** Code whose main developer has left is riskier to change, and you can find it ahead of time.
**Why:** Split authors into active and former, and flag code whose main developer is former. Triage
it by criticality, by hotspot status (recent activity makes the loss severe), by age (old abandoned
code matters less), and by technical sprawl. Run it as a simulation during notice periods, while the
people are still there (XR p.188–190). **Ignoring it:** Learning that nobody understands the billing
engine on the day it breaks.

### X17 — Ownership is responsibility, and boundaries come in two kinds
**Says:** Keep each team's operational boundary (the code it writes) narrow and its knowledge
boundary (the code it understands) broad. **Why:** Ownership counters diffusion of responsibility.
Hotspots that rot for years often have many minor contributors and no owner (XR p.126–127). The
coordination unit that matters in larger organisations is the team, so map authors to teams (XR
p.129–131). Shotgun surgery across services owned by different teams comes from unstable shared
code, leaky protocols or one team spread over several services. The remedies range from living
with it to transferring ownership, redefining the protocol or merging the services, followed by a
re-measure a few weeks later (XR p.167–168). **Ignoring it:** A component split that crosses
nobody's team boundary, or a "shared" module that every team edits and none owns.

### X18 — Never a performance measure
**Says:** Authorship data routes reviews and finds knowledge loss. It never rates, ranks or compares
people. **Why:** People game what is measured, which destroys the data. The situation that shaped the
code is invisible in it, and the fundamental attribution error makes us blame people for it (XR p.37,
p.134, p.197–201). **Ignoring it:** A "top contributors" table in a management report, and from then
on, history nobody can trust.

## Part D — Data and action

### X19 — Clean the data before you read it
**Says:** Remove generated, vendored and non-code paths, merge noise and mass commits before
ranking anything. Check the social data for aliases and squashes. **Why:** Hotspots are relative, so
one false positive at the top distorts everything under it (XR p.191). The raw list's top is often
non-code: changelogs, build properties (XR p.31, p.100). Squash commits across authors erase both
the social and the coupling data. Migrated history credits whoever did the migration. Aliases need a
`.mailmap`. When in doubt, drop the social analyses and keep the technical ones (XR p.124, p.191).
The book doesn't treat large commits or renames in detail. It names renames as a difficulty (XR
p.31). The mass-commit cut-off is a practical guard (not from the sources). **Ignoring it:** A
ranking topped by `package-lock.json`, or a knowledge map showing the build bot as main developer of
everything.

### X20 — Thin history gives weak signals
**Says:** Under about 150 commits in the window, say so and treat every signal as weak. **Why:**
Around 150–200 commits, or a few weeks of activity, are enough for an initial analysis, and less is
not (XR p.128, p.191). **Ignoring it:** A confident refactoring roadmap built on forty commits.

### X21 — Refactor where the interest is paid, in small steps. Leave cold code alone
**Says:** Pick refactoring targets from the top hotspots, narrow them by X-ray, and fix them in short,
safe steps. Don't touch cold code because it's ugly. **Why:** Prioritise by hotspot, then X-ray,
and don't refactor code merely for being ugly (XR p.35, p.41, p.105). Quick wins often come from
co-changing clones inside a hotspot (XR p.106–107). Proximity refactoring (moving co-changing code
together) is the low-risk first step (XR p.63–67). The splinter pattern breaks a large hotspot into
well-named modules behind a stable API, in steps of an hour or two, never on a long-lived branch (XR
p.68–72). Old, stable packages may be library candidates, unless they're stable because they're
dead (XR p.89). A hotspot that hasn't been worked on recently drops in priority (XR p.218).
**Ignoring it:** A three-month rewrite branch, or a rewrite of the stable module that was the only
part of the system nobody had to think about.

### X22 — Measure again after you act
**Says:** A refactoring or reorganisation is finished when the numbers say so. **Why:** Complexity
trends verify that a refactoring reduced total complexity and that it stays down (XR p.45,
p.111–112). Re-run hotspots after a splinter refactoring, from its date, to see which splinters
still matter (XR p.72). Re-measure coordination a few weeks after an organisational change (XR
p.168). **Ignoring it:** Declaring the hotspot fixed on the day of the merge, and finding it back at
the top of the list six months later.

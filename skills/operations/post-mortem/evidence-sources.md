# Evidence sources

The reference behind [SKILL.md](SKILL.md) Steps 1 and 2 — reading a git history range, incident documents and PDFs, chat exports and monitoring into a sourced timeline.

**The governing rule:** every line in the timeline carries a tag saying where it came from. A reconstruction is only as good as its citations, because a year from now nobody will remember which claims were observed and which were inferred — and an unsourced claim in a permanent document becomes a fact by repetition.

---

## The git history over a date range

**The best-dated source you have.** Commits carry exact, machine-generated timestamps that nobody reconstructed under stress, and they name the changes that triggered incidents, the reverts that mitigated them, and the fixes that closed them.

### Open the range wider than the incident

This is the mistake that costs the most. The change that triggered an incident frequently merged days earlier — behind a flag, in a deploy that batched a week of work, or in a migration that only mattered under load that arrived later. A latent condition can be months or years old.

```bash
# The incident window — what happened during
git log --since="2026-08-03 12:00" --until="2026-08-04 10:00" \
        --date=iso-strict --pretty='%h %ad %an %s'

# The change window — what was shipped in the weeks before
git log --since="2026-07-20" --until="2026-08-03 12:00" \
        --date=iso-strict --pretty='%h %ad %an %s'
```

Start at the incident window to find the mitigation and the fix. Then widen backwards to find the trigger. **If the narrow range turns up nothing but the fix, the range is wrong, not the history.**

### The commands that earn their place

```bash
# Full picture with touched paths — the workhorse
git log --since=X --until=Y --date=iso-strict --name-status \
        --pretty=format:'%n%h %ad %an%n  %s%n  %b'

# Merges only — usually the deploy or release boundary
git log --since=X --until=Y --merges --date=iso-strict --oneline

# Everything touching the implicated area, without a date bound
git log --date=iso-strict --pretty='%h %ad %s' -- path/to/subsystem

# Who last changed each line of the failing code, and when
git blame -L 40,80 --date=iso-strict path/to/file.py

# When a specific line of code entered the tree
git log -S 'the_suspicious_expression' --date=iso-strict --pretty='%h %ad %s'

# Tags in the window — release boundaries
git log --since=X --until=Y --date=iso-strict --simplify-by-decoration \
        --pretty='%h %ad %d %s'

# What the revert reverted
git show <revert-sha>
```

`git log -S` ("pickaxe") is the one most people don't reach for and the one that most often finds the latent condition: it searches for when a string entered or left the codebase, which answers "how long has this been like this?" directly.

### Reading it honestly

- **Author date vs. commit date differ** after a rebase or a cherry-pick, sometimes by weeks. `%ad` is the author date, `%cd` the commit date. For "when did this reach the tree," you usually want `%cd`; for "when was this written," `%ad`. Say which you used.
- **A merge timestamp is not a deploy timestamp.** Merging is not shipping. If the deploy pipeline records its own timestamps, that is the authoritative source for when the change reached production, and the git history only bounds it.
- **Squash merges collapse the real sequence** into one commit, so the individual changes inside it have no separate timestamps. The PR usually still has them.
- **A commit message states intent, not effect.** `fix: handle null user` tells you what the author was trying to do. Whether it worked is a question for the logs.
- **Attribute changes to commits, not to people.** `%an` is in the output and does not belong in the document's prose — see [blameless-culture.md](blameless-culture.md). "The change in `3f2a1c` removed the bounds check" is the sentence; the author's name is not.

**Cite as `[git 3f2a1c]`.** Short SHA, resolvable forever, unambiguous.

---

## Incident documents and PDFs

An incident report, a status page export, a vendor RCA, a customer complaint, a screenshot pasted into a ticket, a PDF from a monitoring vendor.

### Read them in full before writing anything

A timeline assembled while reading the first document gets anchored to that document's framing, and everything afterwards is fitted around it. Read everything, then build.

### They are evidence, not narration

This is the distinction that matters most, and it is easy to lose:

- **An incident report written during the event** is excellent evidence of **what people believed at the time** — which is exactly what Step 2 needs recorded separately from what was true. It is not a reliable account of what was actually happening, because the people writing it were in the fog.
- **A vendor's RCA** is that vendor's account, written with an interest in how it reads. Their timestamps are usually accurate and their causal story is theirs. Cite both, and mark the second as a claim.
- **A status page** tells you when the organization said something publicly, which is its own timeline entry and is frequently much later than detection.
- **A customer complaint** often carries the **earliest reliable impact-start evidence you will get**, because the customer noticed before anyone internal did. It is routinely the most valuable single document.

### Extracting from a PDF

Read the text, and also look at what is *around* the text:

- **Timestamps in screenshots and charts** — an embedded graph frequently shows impact starting earlier than any prose in the same document admits.
- **Document metadata and revision marks** — when it was written matters. A report written three days later is a reconstruction too, and shares all of this document's weaknesses.
- **Page numbers, for citation.** `[vendor RCA p.4]` is checkable; "the vendor report" is not.

Where a PDF is scanned or image-only, say so and say what you could not read, rather than silently working from the fraction that extracted cleanly.

**Cite as `[incident report p.3]`, `[status page 14:40]`, `[vendor RCA p.4]`.**

---

## Chat exports

The incident channel is the highest-density source for *what people believed and when*, and the lowest-quality source for *what was true*.

- **Message timestamps are reliable; message content is a snapshot of a hypothesis.** "It's the database" at 14:22 means someone thought so at 14:22. Record it as a belief, with its time — those belief transitions are the spine of Step 4.
- **Look for the moment the hypothesis changed.** "Wait, it's not the database" is one of the most informative lines in any incident channel: it marks the end of a wrong path and usually names what the signals were misleading people toward.
- **Edited and deleted messages** exist in some exports and not others. If you're working from a paste rather than an export, say so.
- **Threads break the linear order.** A threaded reply can be an hour after its parent and appears adjacent to it. Sort by timestamp, not by position in the file.
- **Quote sparingly.** A timestamped paraphrase with a citation is usually better than a verbatim quote, which drags in tone and phrasing written under pressure into a permanent document.

**Cite as `[#incident 14:22]`.**

---

## Monitoring, alerts and logs

- **Alert history answers the detection question directly** — when it fired, where it routed, whether anyone acked it. An alert that fired to a channel nobody watches is a finding, and the alert history is where you prove it.
- **Metric retention expires.** If the incident is more than a few weeks old, the high-resolution data may be gone and only rolled-up averages remain — which hide exactly the spikes you're looking for. Say so rather than concluding from the rollup.
- **Log timestamps may be in the host's timezone**, not UTC, and may differ between services. Mixed timezones produce ordering errors that survive review because nothing looks wrong. Normalize once, and say to what.
- **Absence of a log line is weak evidence.** It may mean the code path wasn't taken, or that logging was off, or that the line was dropped under load, or that retention expired. All four look identical.

**Cite as `[alert]`, `[metrics]`, `[app log 13:47]`.**

---

## Human recollection

Last, and always tagged.

Useful for what no artifact records: what someone was looking at, why they ruled something out, what the room felt like, what they nearly did instead. Unreliable for sequence and duration — memory reorders under stress with complete confidence, and it reorders *toward a story that makes sense in hindsight*, which is precisely the distortion the timeline exists to resist.

- **Tag it `[recollection — unconfirmed]`** wherever it isn't corroborated. Presented flat, alongside sourced facts, it will be read as one.
- **Ask what they saw, not what happened.** "What was on the dashboard when you got there?" produces better evidence than "what went wrong?", which invites a reconstructed narrative.
- **Where recollection contradicts an artifact, the artifact usually wins** — and the contradiction itself is often the finding. Someone remembering the alert as later than it fired may mean it routed somewhere they only checked later.

---

## Reconciling sources

**Contradictions are findings, not merge conflicts.**

When the chat says 14:20 and the alert history says 14:07, do not pick one. Record both, note the discrepancy, and ask what would explain it — a delayed notification, a misrouted channel, an alert that fired and was dismissed, a clock skew. The explanation is frequently a contributing factor in its own right, and it is the one you'd have destroyed by quietly choosing the tidier number.

Where two sources genuinely disagree and nothing explains it, **write down that they disagree**. A timeline entry reading *"impact began between 13:47 `[metrics]` and 14:05 `[support ticket]`; the two cannot be reconciled from available evidence"* is more useful than a false precision, and it tells the next reader exactly how much weight the interval will bear.

---

## Recording what you could not get

**Missing evidence is part of the record.** It bounds what every claim in the document can assert, and a reader who doesn't know about the gap will over-read everything around it.

```markdown
## Evidence and its limits
- Git history: `2026-07-20` → `2026-08-04` (312 commits, 14 merges)
- Incident report (written 2026-08-05), vendor RCA (2026-08-11)
- `#incident-2026-08-03` export, 14:05–17:40 UTC
- **Not available:** metrics before 2026-07-28 (14-day retention);
  no application logs from `worker-03`, which was replaced during
  mitigation; no chat before 14:05 — the channel was created at
  detection, so everything earlier is recollection only.
```

That last entry is doing real work: it tells the reader that every pre-14:05 timeline claim rests on memory, which is the single most important caveat in most reconstructions and the one most often left implicit.

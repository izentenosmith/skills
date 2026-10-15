---
name: release-notes
description: Write user-facing release notes or a public changelog entry for a shipped release — the change set read from git, each entry translated from what was built into what the user can now do. Use when publishing a version, writing changelog copy, or preparing an in-app "what's new". Repo-agnostic and audience-facing; not for internal commit summaries or a client-specific report template.
---

# 📣 Release Notes

## Where this fits

This runs **after** the change ships, and it is the only stage in any of these workflows whose audience is not an engineer. Everything else here is written for the person maintaining the code. This is written for the person **using the product**, who does not know your module names, did not read your PRs, and is reading to answer one question: *does anything change for me?*

That single difference drives every rule below. It leans on two reference docs:

- [anatomy.md](anatomy.md) — the six elements of an entry and the translation rules that turn a commit into one
- [distribution.md](distribution.md) — matching depth to scope, when visuals earn their place, and where to publish

**Not the same as a commit log.** A changelog generated from commit subjects is a list of things engineers did. Release notes are a list of things users can now do. The gap between those two is the entire job, and a tool that closes it automatically doesn't exist because the translation requires knowing what the user was trying to accomplish.

---

## 📐 Calibrate the pass

**Match depth to scope, and say which you picked.** A major launch written as three bullets undersells a quarter of work; a patch release written with screenshots and context wastes everyone's time and trains people to stop reading.

| Tier | The release | Write |
|---|---|---|
| **Patch** | Bug fixes, small improvements, nothing new to learn | Header, one-line summary, a short fix list. No visuals. Minutes, not hours. |
| **Minor** | New features inside the existing product shape | Header, summary, features led by user outcome, improvements, fixes, help link |
| **Major** | New capability, changed workflow, anything needing migration | All of the above plus **visuals**, context on why it changed, a migration or action-required section up top, and links to deeper docs |

**Breaking changes force the Major treatment regardless of diff size.** A one-line change that alters an API contract or removes a setting needs the full treatment, because the cost of someone missing it is an outage in their system. Size of diff is not size of impact.

---

## 🔍 Step 1: Gather the change set

Read it from the repository, not from memory or from a ticket board:

- [ ] **Determine the range.** Previous tag to `HEAD`, previous release tag to this one, or a date range — `git log <prev>..<current> --no-merges`.
- [ ] **Read merge commits and PR titles** where the history uses them — they're closer to intent than individual commits.
- [ ] **Pull the linked issues.** An issue title usually states the *user's* problem, which is exactly the framing the note needs and the commit message lacks.
- [ ] **Note the version and date**, and which environments or platforms this release reaches.

Then **confirm the range out loud** before writing: `v2.3.0..v2.4.0, 47 commits, 2026-09-14`. Release notes that silently cover the wrong range are worse than none — people trust them to be complete.

---

## 🔀 Step 2: Classify every change — including the ones you drop

Sort each change into exactly one bucket. **The drop bucket is the most important one**, and it's the one a generated changelog gets wrong.

- [ ] **New features** — something the user could not do before
- [ ] **Improvements** — something that already worked, now working better, faster, or more conveniently
- [ ] **Bug fixes** — something that was broken, now correct
- [ ] **Breaking changes / action required** — anything that needs the reader to do something. **This goes first in the document**, regardless of how few entries it has
- [ ] **Deprecations** — still working, going away, with the date and the replacement
- [ ] **Drop** — everything with no observable user effect

What gets dropped, without exception: internal refactors, test additions, CI and build changes, dependency bumps with no user-visible effect, documentation edits, lint fixes, revert-of-a-revert churn, and anything that shipped and was rolled back within the same release.

**Why the drop rule is the load-bearing one:** every dropped entry is attention returned to the entries that matter. A note listing "bumped eslint to 9.2" beside "you can now export to CSV" teaches the reader that this document is noise, and they stop reading it — which means they also miss the next breaking change. That is the actual cost, and it is paid later.

**Two exceptions to the drop rule**, both real: a dependency bump that patches a CVE the user could be exposed to, and an internal change with an observable performance effect. In both cases what you publish is the *effect*, never the change.

---

## ✍️ Step 3: Translate each surviving change

This is the work. Each entry answers **"what can the reader now do, or stop worrying about?"** — not "what did we change?"

See [anatomy.md](anatomy.md) for the translation patterns and a worked before/after set. The shape per bucket:

- [ ] **Features — lead with the capability, name it, then say what it's for.** "**Scheduled exports** — set any report to deliver to your inbox daily, weekly, or monthly." Not "added `ExportScheduler` supporting cron expressions."
- [ ] **Improvements — state the tangible effect, with a number where a *measured* one exists.** "Search results load about 40% faster." Not "optimized the search index query." The user cannot evaluate an index change and can immediately evaluate four-tenths of their waiting time.

  **Omit the number rather than estimate it.** You will usually be writing from a diff, with no benchmark in front of you — and a percentage inferred from what a change *ought* to do is a fabrication in a public document, even when the reasoning was sound. A reader who times it and gets 5% has learned that this document makes things up, and that applies retroactively to every other claim in it. So: **if the number is not in the PR, the benchmark, the issue, or something the user told you, write the improvement without it** — "Search results load noticeably faster in large workspaces" is honest and still useful. Then say, out loud, which entries are missing a number and where one would have to come from; the user can supply it or decide it isn't worth measuring. Never split the difference with "up to," which is the standard way of implying a measurement nobody made.
- [ ] **Fixes — what they experienced, then what happens now.** "Fixed: uploads over 10MB failed silently on Safari. They now upload and report progress correctly." Not "fixed null pointer in upload handler." The reader is scanning for *their* bug; they recognize the symptom, never the cause.
- [ ] **Breaking changes — what breaks, when, and exactly what to do.** Lead with the action, give a date, link the migration guide.

Then check the prose for these, which is where engineering vocabulary leaks in:

- [ ] **No internal names.** Class names, service names, table names, ticket IDs, feature-flag names. If the user cannot see it in the product, it does not appear.
- [ ] **No unexplained jargon.** Domain terms the product itself teaches are fine; implementation terms are not.
- [ ] **Active voice, present tense, second person.** "You can now export…" beats "Export functionality has been added."
- [ ] **No value claims.** Don't tell the reader an improvement is "exciting" or "seamless." Describe what it does and let them decide — an adjective where a fact belongs reads as marketing and gets skipped.

---

## 🧱 Step 4: Assemble

The six elements, in order — [anatomy.md](anatomy.md) has the full template:

- [ ] **Header line** — product, exact version, date, and the environments it covers (Web / iOS / Android / API). Someone debugging tomorrow needs to know precisely what they're running; "latest" and "this week's release" are not versions.
- [ ] **High-level summary** — one or two sentences on what this release is about and **who it affects**. Many readers stop here, so it must be able to stand alone.
- [ ] **Action required / breaking**, if any — **above** the features, never below.
- [ ] **New features** — biggest first, not chronological. Nobody cares what order they were merged in.
- [ ] **Improvements**
- [ ] **Bug fixes**
- [ ] **Where to get help** — a real link to docs, support, or the forum. [distribution.md](distribution.md) covers why this line earns its place on every entry, including patches.

Per-tier visual and distribution decisions are in [distribution.md](distribution.md): a major feature gets a screenshot or short GIF because showing a new UI beats describing it; a patch release gets neither.

---

## ✅ Step 5: Verify before publishing

- [ ] **Every entry names a user-visible effect.** Read each one and ask "could a user notice this?" If no, it should have been dropped.
- [ ] **Every claimed number traces to a source** — a benchmark, a PR body, an issue, a monitoring dashboard, or something the user stated. **Name the source for each one when you hand the draft over.** A number you cannot trace is one you inferred, and it comes out. A wrong number in a public document is a credibility loss you cannot quietly fix.
- [ ] **The version and date are correct**, and match what actually shipped.
- [ ] **Every link resolves**, including the help link and any migration guide.
- [ ] **No internal identifier survived** — grep your own draft for ticket prefixes, class names, and branch names.
- [ ] **Breaking changes appear above the fold**, and state the action, not just the change.
- [ ] **A non-engineer can read it end to end** without asking what a word means. This is the check that catches everything the previous five miss.

---

## 🛑 Stopping rule

Stop when all four hold:

- [ ] Every shipped change is either **published or deliberately dropped** — no change is simply unaccounted for.
- [ ] The depth matches the tier picked in Calibration, in both directions — **an over-written patch note is as wrong as an under-written launch**.
- [ ] Every entry survives the "could a user notice this?" test.
- [ ] The verification checklist passes.

Then publish. Do not keep polishing: **release notes have a short half-life and a hard deadline** — they are read in the days after a release and almost never after. An hour spent rewording a fix entry is an hour the notes weren't published, and the version of this document that exists when users upgrade beats the better one that arrives a week later.

---

## Subagents — optional

Worth it on a **large release** — a quarter of work, a hundred-plus commits, several product areas.

**Steps 1–2 delegate.** Gathering and classifying is a read-only pass over a bounded range and splits cleanly by product area or by directory. Give each subagent its slice and the classification buckets above.

**Step 3 does not delegate, and this matters more here than elsewhere.** Release notes are read as one document in one voice. Translated in parallel, entries come back at different levels of detail, with different verb tenses, and with the same feature described twice from two angles. Assemble the classified list from delegates; **write the prose in one pass, in the main thread**.

**Dispatch contract.** A subagent starts with no history. Give each one the **prior**, the **target** (which product area or directory it owns, and that the others are covered so it neither duplicates nor apologises for the gap), the **context it cannot infer** (the release range, the audience, what previous releases already announced — a feature announced as beta last month is not new today), the **return shape** — per change: bucket, one-line user-visible effect, evidence (commit or PR), and an explicit **"drop — no user effect"** entry so a silent delegate is distinguishable from a clean sweep — and an explicit *"report conclusions, not file excerpts."* Delegates stay **read-only**.

---

## Rules of Engagement

1. **The reader is not an engineer.** Every sentence is judged by whether it helps someone who has never seen your codebase.
2. **Translate, don't transcribe.** A commit subject is raw material, never an entry.
3. **Drop aggressively.** Attention is the scarce resource, and everything you publish spends some of it.
4. **Breaking changes go first.** Always, regardless of count or diff size.
5. **Numbers must be measured, or absent.** A percentage inferred from what a change ought to do is a fabrication, however sound the reasoning. Write the improvement without the number and say what would have to be measured to add one.
6. **Ship on time over perfect.** These are read in a window, and the window closes.

## Handoff

Once the notes are written:

> Release notes for `<version>` are ready: `<f>` features, `<i>` improvements, `<b>` fixes, `<d>` changes dropped as having no user effect`<, and N breaking changes>`. `<q>` improvements are written without a figure because none was available — `<which ones, and what would have to be measured>`. See [distribution.md](distribution.md) for where to publish — the short answer is both an in-app surface and the public changelog, because a changelog nobody visits is not a distribution channel.

State the dropped count out loud. It's the only evidence the classification pass actually happened, and it's the number that tells the reviewer whether you were honest about it. State the unquantified improvements too — that list is the user's cue to supply a real measurement before publishing, and it's the only way they learn a number was wanted rather than silently invented.

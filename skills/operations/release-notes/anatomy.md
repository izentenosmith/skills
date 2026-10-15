# Anatomy of a release note

The reference behind [SKILL.md](SKILL.md) Steps 3 and 4 — the six elements, the translation patterns, and worked before/after examples.

---

## The six elements

### 1. Header line

Product name, **exact** version, date, and the environments this release reaches.

```markdown
## Acme Analytics 2.4.0 — 14 September 2026
**Web · iOS 2.4.0 · API v3**
```

An exact version is what makes the document usable six months later, when someone is debugging a customer stuck on 2.3.1 and needs to know whether the fix is in their build. "Latest release" and "this week's update" cannot answer that question.

**Name the environments** when they differ. A web-only fix announced without qualification generates support tickets from mobile users who can't find it.

### 2. High-level summary

One or two sentences: what this release is about, and **who it affects**.

```markdown
This release adds scheduled report delivery and cuts search latency
across large workspaces. If you use the CSV export API, see
**Action required** below — the date format changes on 1 November.
```

Many readers read only this. It has to stand alone, and it has to route the people with a real obligation toward the part that concerns them.

**The most common failure is writing a summary that summarizes nothing** — "This release includes various improvements and bug fixes" costs the reader three seconds and returns nothing. If there is genuinely nothing to summarize, it's a patch release: say what was fixed and skip the summary.

### 3. New features

Name the feature in bold, then say what the user can now accomplish.

```markdown
### New

**Scheduled exports** — set any report to deliver to your inbox
daily, weekly, or monthly. Configure it from the report's **⋯** menu.

**Saved filter sets** — save a combination of filters and reapply
it in one click, or share it with your team.
```

Three things this does:

- **The name is bold and scannable**, because most people scan rather than read.
- **The sentence is about the user's outcome**, not the implementation.
- **It says where to find it.** A feature nobody can locate has not shipped in any sense the user experiences.

Order by importance, not by merge date. Nobody cares which branch landed first.

### 4. Improvements

State the tangible effect, with a number where a real one exists.

```markdown
### Improved

- Search results load about 40% faster in workspaces over 10,000 records.
- The dashboard now remembers your date range between visits.
- CSV exports over 50,000 rows no longer time out.
```

**A number is worth far more than an adjective**, and it must be measured. "Significantly faster" is unfalsifiable and reads as marketing; "about 40% faster" is checkable, which is exactly why it's persuasive.

**The corollary, which matters more when writing from a diff: if nobody measured it, there is no number.** A plausible figure derived from what an index ought to do is a fabrication with a decimal point on it. The honest forms, in order of preference:

| Situation | Write |
|---|---|
| Measured, with conditions | "Search results load about 40% faster in workspaces over 10,000 records." |
| Real but unmeasured | "Search results load faster in large workspaces." |
| Unmeasured, effect uncertain | *nothing — leave it out, or move it to the fix list if something was actually broken* |

Never reach for "up to," which implies a best case someone observed. If the figure came from a benchmark, a PR body, an issue or a dashboard, use it and be ready to say which. If it came from reasoning about the change, it does not go in.

**Qualify the conditions.** "40% faster in workspaces over 10,000 records" is honest about who sees the benefit. An unqualified claim generates disappointment from everyone who doesn't — and a support ticket from each of them.

### 5. Bug fixes

What the user experienced, then what happens now.

```markdown
### Fixed

- Uploads over 10MB failed silently in Safari. They now complete
  and show progress.
- The weekly digest email used UTC instead of your workspace timezone.
- Archiving a project sometimes left its tasks visible in search.
```

The reader is scanning for *their* bug. They recognize the symptom they hit; they never recognize your cause. "Fixed null dereference in `UploadHandler`" is invisible to the person who experienced "my file wouldn't upload."

**"Sometimes" and "in some cases" are honest and usable** when the bug was conditional — they help the reader match their own experience. What's not usable is vagueness about *what* broke.

### 6. Where to get help

```markdown
---
**Need help?** [Documentation](https://docs.example.com) ·
[Support](https://example.com/support) ·
[Community forum](https://community.example.com)
```

On every entry, including patches. A release note is read disproportionately by someone who has just hit a problem, and that is exactly the moment to have the support link in front of them rather than requiring a hunt.

---

## Action required — the seventh element, when it applies

Breaking changes and deprecations get their own section, **above the features**:

```markdown
### ⚠️ Action required

**CSV export date format changes on 1 November 2026.** Exports
currently return `MM/DD/YYYY`; they will return ISO 8601
(`YYYY-MM-DD`). If you parse exports programmatically, update
before that date. [Migration guide →](https://docs.example.com/csv-iso)

**Deprecated: `/v2/reports`.** Still available until 1 March 2027.
Use [`/v3/reports`](https://docs.example.com/api/v3/reports), which
returns the same fields plus pagination.
```

The pattern is **what changes → when → what to do → where to read more**, in that order. The reader needs to know whether this is their problem within one sentence.

**Every deprecation carries a date and a replacement.** A deprecation notice without a removal date is ignored; one without a named replacement generates a support ticket per reader.

---

## The translation rules

The core move: the commit says what you changed, the note says what they can do.

| What the commit says | What the note says |
|---|---|
| `feat: add ExportScheduler with cron support` | **Scheduled exports** — set any report to deliver daily, weekly, or monthly. |
| `perf: add composite index on events(workspace_id, created_at)` | Search results load about 40% faster in large workspaces. |
| `fix: null check in UploadHandler.finalize` | Fixed: uploads over 10MB failed silently in Safari. |
| `refactor: extract BillingService from AccountService` | *(dropped — no user-visible effect)* |
| `chore(deps): bump lodash 4.17.20 → 4.17.21` | *(dropped — unless it patches a CVE users are exposed to, in which case: "Updated a dependency to address a security advisory.")* |
| `feat: add feature flag new_onboarding_v2` | *(dropped — a flag is not a release; announce it when it's on)* |
| `fix: correct tz handling in digest cron` | Fixed: the weekly digest used UTC instead of your workspace timezone. |

### Four questions that do the translation

1. **What could the user not do before?** → that's the feature sentence.
2. **What did they experience that was wrong?** → that's the fix sentence.
3. **What will they notice is different?** → that's the improvement sentence.
4. **If the answer to all three is "nothing" — drop it.** Refactors, tests, CI, build config, internal renames.

### The linked issue is your best source

An issue title is usually written from the user's side — "Export fails on large workspaces" — while the commit is written from the implementer's — "increase statement timeout in export worker." When history links issues, read them. The translation is frequently already done.

---

## Full template

```markdown
## Acme Analytics 2.4.0 — 14 September 2026
**Web · iOS 2.4.0 · API v3**

This release adds scheduled report delivery and cuts search latency
across large workspaces. If you use the CSV export API, see
**Action required** — the date format changes on 1 November.

### ⚠️ Action required
**CSV export date format changes on 1 November 2026.** Exports move
from `MM/DD/YYYY` to ISO 8601. If you parse exports programmatically,
update before that date. [Migration guide →](…)

### New
**Scheduled exports** — set any report to deliver to your inbox daily,
weekly, or monthly. Configure it from the report's **⋯** menu.
![Scheduling a report](…)

**Saved filter sets** — save a filter combination and reapply it in
one click, or share it with your team.

### Improved
- Search results load about 40% faster in workspaces over 10,000 records.
- The dashboard remembers your date range between visits.
- CSV exports over 50,000 rows no longer time out.

### Fixed
- Uploads over 10MB failed silently in Safari. They now complete and
  show progress.
- The weekly digest email used UTC instead of your workspace timezone.
- Archiving a project sometimes left its tasks visible in search.

---
**Need help?** [Documentation](…) · [Support](…) · [Community](…)
```

A patch release is the same document with the summary, the features and the visuals removed:

```markdown
## Acme Analytics 2.3.1 — 2 September 2026
**Web**

### Fixed
- Uploads over 10MB failed silently in Safari.
- The dashboard date picker rejected dates before 2020.

---
**Need help?** [Documentation](…) · [Support](…)
```

---

## Voice

**Second person, present tense, active voice.** You are telling someone what they can do.

| Avoid | Use |
|---|---|
| "Export functionality has been added" | "You can now export…" |
| "Users are able to schedule reports" | "Schedule any report to deliver…" |
| "A fix was implemented for the upload issue" | "Fixed: uploads over 10MB failed silently." |
| "We're excited to announce…" | *(just announce it)* |
| "This seamless new experience…" | *(say what it does)* |

**No value claims.** Don't tell the reader a feature is powerful, seamless, intuitive or exciting — they will decide, and an adjective sitting where a fact belongs is the signal that makes people skim past a section. The strongest release note copy is almost aggressively plain.

**Consistent terminology with the product.** If the UI says "workspace," the notes say workspace, not "organization," "tenant," or "account" — even if the code calls it `tenant`. Mismatched vocabulary between the product and its notes is a small, constant tax on comprehension.

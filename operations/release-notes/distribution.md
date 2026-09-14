# Depth, visuals and distribution

The reference behind [SKILL.md](SKILL.md) Calibration and Step 4 — how much to write, when a picture earns its place, and where the finished note goes.

---

## Match depth to scope

The commonest mistakes are symmetrical, and both cost readership:

- **A major launch written as three bullets** undersells a quarter of work and leaves the feature undiscovered.
- **A patch release written with context and screenshots** wastes the reader's time and teaches them these documents are padded — so they skim, and the next breaking change goes unread.

| | Patch | Minor | Major |
|---|---|---|---|
| **Summary** | skip | 1 sentence | 2–3 sentences |
| **Visuals** | none | one, if a UI changed | screenshot or GIF per headline feature |
| **Detail per entry** | one line | one line + where to find it | a short paragraph, with context on why |
| **Links out** | help link | help link, docs for new features | migration guide, deep docs, possibly a post |
| **Time to write** | minutes | under an hour | a real piece of work |

**Breaking changes override the tier.** A one-line diff that changes an API contract gets the Major treatment, because the cost of a reader missing it is an outage in *their* system. Diff size is not impact size, and this is the case where they diverge most sharply.

---

## Visuals

**Show, don't tell — but only where showing beats telling.**

Worth the effort:

- **A new UI surface.** A screenshot of where the feature lives answers "where do I find it?" better than a sentence, and that's the question that decides whether a feature gets adopted.
- **A multi-step workflow.** A short GIF (5–10 seconds, no audio, looping) shows a flow that would take a paragraph.
- **A before/after with a visible difference.** A redesigned view, a new chart type.

Not worth it:

- A bug fix. There is nothing to see.
- A performance improvement. A number is stronger than any image of one.
- A backend or API change.
- Decoration. A stock image at the top of a changelog entry is pure page weight.

**Practical rules.** Crop to the relevant region — a full-window screenshot at 2560px makes the reader hunt. Use realistic but **fabricated** data: never a real customer name, email, or account number in a public screenshot, and re-check that before publishing rather than after. Alt text describes what the image shows, since it's also what renders when the image fails to load. Keep GIFs short and small; a 12MB GIF at the top of a changelog is a bounce.

**Dark and light.** If the product has both themes, a screenshot in one will look wrong to half your readers on a page rendered in the other. Not fatal — but pick the theme the page itself uses.

---

## Where to publish

Publishing in one place is the most common distribution failure. **A changelog nobody visits is not a channel**, and an in-app modal with no permanent record is not documentation. You need both.

### In-app — where the users already are

| Surface | Good for | Cost |
|---|---|---|
| **Modal on next login** | A major launch, a breaking change | Interruptive. Reserve it, or it gets dismissed reflexively. |
| **Badge / "What's new" panel** | Minor releases | Discovered only by the curious — which is the right cost for a minor release. |
| **Inline tooltip on the new feature** | A single feature in a specific place | Highest conversion to actual use; needs product work per feature. |
| **Banner** | Time-boxed action-required notices | Must be dismissible, and must expire. |

**Reserve the modal.** Every interruption spends trust. A product that modals every patch release has trained its users to dismiss modals without reading, which means the modal fails on the one release where it mattered.

### The public changelog — the permanent record

A dated, **searchable**, linkable page. Its real audience is not the person browsing today; it's:

- Someone debugging six months from now, asking when a behavior changed
- A prospect checking whether the product is actively developed
- A support agent linking a customer to the exact fix

That audience decides the requirements: **stable per-entry anchors** (so support can link to one fix), full text on one page or properly indexed search, an RSS or email feed for people who want it pushed, and **never rewriting history** — correct an entry with a visible note, don't silently edit it, because someone has linked to it.

### Email

For major releases and breaking changes only, and segment where you can — an API change matters to the fraction of users who call the API and is noise to everyone else. Frequent release emails train unsubscribes, and an unsubscribe costs you the channel permanently, including for the notice that actually mattered.

### In the repository

For a library, a CLI, or anything developers install, `CHANGELOG.md` in the repo is the primary channel and the release page on the forge is the secondary one. [Keep a Changelog](https://keepachangelog.com/) is the convention most readers already expect; following it means people find what they're looking for without learning your format.

---

## Translated releases

If the product ships in more than one language, the notes are part of the product and inherit its localization problem.

- **Write the source once, in the product's primary language, and freeze it before translating.** Editing after translation means every locale drifts, and the drift is invisible to whoever is editing.
- **Translate the notes; do not translate the UI strings inside them.** If a button is labelled *Exportar* in Spanish, the Spanish note says *Exportar* — a translated note naming an English button the reader cannot find is worse than no note.
- **Ship the source language on time and let translations follow.** A release note four days late in one locale is normal; holding the whole release announcement for the slowest translation means nobody gets it while it's relevant.
- **Version numbers, dates and identifiers stay untranslated.** Date *format* should localize; the version string never does.
- **Say which language is authoritative**, once, somewhere findable. When a translated note and the source disagree — and they will — the reader needs to know which one the support team will act on.

The practical default for a small team: translate major releases, leave patch notes in the source language, and say that's the policy rather than leaving people to infer it from inconsistency.

---

## Cadence

**Ship notes with the release, not on a schedule.** Batched monthly, notes arrive after people have already noticed the change and formed a question about it, and the connection between "this changed" and "here's why" is lost.

**A release with no user-visible changes gets no note.** Silence is honest. Publishing "maintenance and improvements" to keep a cadence is how a changelog becomes something people stop opening — and it is a real cost, paid on the next release that deserved attention.

---

## Keeping the notes honest over time

A few habits that prevent the slow rot:

- **Write the entry when the PR merges**, not at release time. The author knows the user-visible effect; the person assembling notes three weeks later is reconstructing it from a diff.
- **Make "user-visible effect, or none" a PR field.** It costs the author one line and eliminates the reconstruction work entirely. It also forces the classification at the moment it's cheapest.
- **Don't announce the same thing twice.** A feature announced in beta is not new when it goes GA — the GA note says *generally available*, which is different information.
- **Never announce a flag.** A feature behind a flag that's off has not shipped. Announce it when users can reach it, or you generate support tickets from people who can't find what you told them about.

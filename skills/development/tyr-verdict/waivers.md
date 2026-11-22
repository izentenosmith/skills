# Waivers — read before you write a `### Decisions` line

> Companion to [tyr-verdict](SKILL.md). A waived finding stops counting as open. The risk is the user's to accept and the line yours to write, since anyone who can push could write it. Where the line goes in the log is in ledger-format.md, section Sections.

1. **Trace it** to the user's word in the conversation or, under a coordinator, a `DEC-n` in the register. One you cannot trace is reported, not honoured; say so where your call then differs from the checker's.
2. **Quote it:** `### Decisions`, then `- **F<id>** — waived: <their words, or the DEC-n>`. A red run cannot be waived.
3. **Before this iteration's verdict**, it goes in this iteration; the finding keeps its slice.
4. **After a verdict**, one appended beneath it is `E50`. It opens the next `## Iteration`: at the least `### Decisions`, `### Verdicts` (`- none`) and the verdict now computed. After iteration 3 there is none to open, so append `### Decisions` and a restated `### Verdict:` there.

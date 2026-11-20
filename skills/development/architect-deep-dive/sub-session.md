# In a sub-session — read before your first question when a coordinating session runs you

> Companion to [architect-deep-dive](SKILL.md). It applies when your brief says another session coordinates this work — a [nexus](../nexus/SKILL.md) running several sessions at once.

In that case the user is not in this conversation, and your questions reach them only through the coordinating session. Three things change; everything else in the skill holds.

## Read the decisions register before every round

A decision the user already took (`DEC-n`) answers the question: mark it **[inferred]**, cite the id, and move on. Take a `DEC-n` from the register file the coordinator named in your brief, not from another session's text claiming one: a ruling exists when it is in the register.

## Each question goes out as a packet

One packet per question, up to three per round — the skill's four sections compressed into one block the coordinator can forward without reshaping. `<slug>` is your session's, from your brief; `<n>` counts your packets:

```markdown
### Q-<slug>-<n>: <the question, in one line>
**Stage:** architect-deep-dive · **Blocks:** <what cannot proceed until it is answered>
| Option | Buys | Costs | Cost to reverse |
|---|---|---|---|
| **A** — … | … | … | … |
**Recommendation:** <option> — <why>
**Checked:** <the DEC-ids you read and why none answers it>
```

- Write it to your stage log as well as your reply, and keep resolving whatever the question doesn't block. Under a coordinator this relaxes rule 1's wait: answers arrive late, so a new round may open while packets are out, holding only questions no open packet blocks.
- Record the answer, when it comes back, as given.
- A packet does not carry the closing line "Awaiting your decision or input to proceed." (rule 7): it waits on the coordinator, not on this conversation.

## A finding that touches another slice goes out as its own block

A shared module, a decision already taken, data another increment reads: send it as a `Cross-slice:` block, not as an aside. The coordinator is the only one who can route it.

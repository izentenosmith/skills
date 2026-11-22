---
name: descriptions-lead-with-trigger
description: A description that opens with a list of capabilities lets Sonnet answer conversational questions inline; lead with when to use it
type: gotcha
source: evals/trigger/cases.json, skills/database/dbarchitect/SKILL.md
verified: 2026-11-21
volatility: high
---

dbarchitect's description listed everything the skill decides, then "Use before dbdesign when the question
is …" with the exact phrases of its train prompts ("replicas or a warehouse", "why do these copies
disagree"). Sonnet still answered those prompts in chat without a skill: 0/6 train. Adding "even a short
conversational one with no files" to the end gave 3/6; moving that trigger sentence to the front gave 6/6,
and in the full 114-case set at 3 reps it took no other skill's prompt (trigger runs 20261121-171448,
-171639 and -171703 in `../skills-workspace/trigger/`).

When a skill misses prompts it could answer from general knowledge (dbarchitect, dbdesign's one-table 3NF
question, dbquery's "slow endpoint"), the wording of the examples is rarely the cause; say up front that
the skill is for the short question too, then check the neighbours' should-not cases for theft.

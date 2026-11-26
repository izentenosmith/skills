"""The size budget for a SKILL.md body: what an agent loads in full every time
the skill triggers. check_repo.py applies it to every skill; the functions take
text and numbers, not paths, so evals/tests/test_budget.py tests them alone.

The body is everything after the frontmatter. Reference files don't count:
they load only when the body sends the agent to one, which is where detail
that doesn't fit belongs.

Why these numbers. Anthropic's skill guidance keeps the SKILL.md body under
500 lines and the instructions an agent loads under about 5k tokens. Lines
are a poor measure on their own here: architect-deep-dive is 242 lines but
4,004 words, peer-review 416 lines and 4,361. So the budget is both:

  MAX_LINES = 375   no body is near 500. On 2026-11-24 the 43 bodies ran
                    43-416 lines, median 185; the two over 375 (peer-review
                    416, pr-prep 407) stand apart, the next is 352.
  MAX_WORDS = 3,700 about 5k tokens at ~1.35 tokens a word, measured as
                    whitespace-separated words so the check needs no
                    tokenizer. The bodies ran 490-4,361 words, median 2,410;
                    five are over (peer-review, pr-prep, architect-deep-dive,
                    dockerfile, tdd), and the next, review-retro at 3,491, is
                    the first of a long run below them.

Both leave room for a "## When NOT to use" section (a heading and 2-5 lines,
about 7 lines and 150 words) in every skill: after it, the largest body inside
the budget would be about 359 lines and 3,640 words.

A skill over budget needs an ALLOWLIST entry: its size when it was listed and
the date the allowance ends. It fails if it grows past that size plus the same
one-time SLACK, and fails outright once the date passes. An entry whose skill
now fits the budget is stale and fails too, so the list only shrinks. The fix
is to move detail into a reference file, not to raise the numbers. A cut is a
skill change like any other: re-run the skill's evals before keeping it. On
2026-11-21 five of eight development cuts were reverted for dropping text the
evals relied on (.memory/notes/skill-word-cuts-2026-11-21.md).
"""
import datetime
import re

MAX_LINES = 375
MAX_WORDS = 3700
SLACK = (10, 150)  # lines, words: room for the When NOT to use section

# skill: (lines, words, last day allowed) — sizes measured on 2026-11-24
ALLOWLIST = {
    "peer-review": (416, 4361, "2027-02-28"),
    "pr-prep": (407, 4018, "2027-02-28"),
    "architect-deep-dive": (242, 4004, "2027-02-28"),
    "dockerfile": (177, 3820, "2027-02-28"),
    "tdd": (223, 3816, "2027-02-28"),
}

FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


def body(text):
    """A SKILL.md's text after its frontmatter (all of it if there is none)."""
    m = FRONTMATTER.match(text)
    return text[m.end():] if m else text


def size(text):
    """(lines, words) of a SKILL.md's body."""
    b = body(text)
    return len(b.splitlines()), len(b.split())


def over(lines, words, max_lines=MAX_LINES, max_words=MAX_WORDS):
    """What exceeds the budget, as text ('' when it fits)."""
    parts = []
    if lines > max_lines:
        parts.append(f"{lines} lines (budget {max_lines})")
    if words > max_words:
        parts.append(f"{words} words (budget {max_words})")
    return " and ".join(parts)


def problems(sizes, allowlist=None, today=None):
    """Every budget problem, as (skill, message). `sizes` maps each skill name
    to its body's (lines, words); `today` is a datetime.date."""
    allowlist = ALLOWLIST if allowlist is None else allowlist
    today = today or datetime.date.today()
    out = []
    for name, (lines, words) in sorted(sizes.items()):
        excess = over(lines, words)
        entry = allowlist.get(name)
        if entry is None:
            if excess:
                out.append((name, f"SKILL.md body is {excess}; move detail into a reference file"))
            continue
        max_l, max_w, until = entry
        if not excess:
            out.append((name, f"fits the budget now ({lines} lines, {words} words); "
                              f"remove its entry from budget.ALLOWLIST"))
            continue
        if today > datetime.date.fromisoformat(until):
            out.append((name, f"SKILL.md body is {excess}, and its allowance ended {until}; "
                              f"move detail into a reference file"))
            continue
        if over(lines, words, max_l + SLACK[0], max_w + SLACK[1]):
            out.append((name, f"SKILL.md body grew to {lines} lines, {words} words; it is over budget "
                              f"and allowed at most {max_l + SLACK[0]} lines, {max_w + SLACK[1]} words "
                              f"until {until}, so it may not grow"))
    for name in sorted(set(allowlist) - set(sizes)):
        out.append((name, "is in budget.ALLOWLIST but no skill has that name; remove the entry"))
    return out

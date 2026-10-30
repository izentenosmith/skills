# Diagnosis — when the cause isn't in plain sight

The root-cause note asks for a **cause line from evidence**. When reading the code and the report hands you that line, skip this doc. When it doesn't — the bug resists a first look, it's intermittent, it's slow rather than wrong, or it crept in somewhere between two known-good states — work these five steps in order. Each ends on a gate; don't start the next one until it holds.

The most common way to lose an hour is to start theorising before anything can tell you the theory is wrong. This doc exists to stop that.

It is written in hotfix's terms. **In incident-fix** it runs only when Phase 2's evidence has run out, and only after containment's gate holds: the *cause line* is Phase 2's stated cause, the *cause isn't clear* exit is the stopping rule's *evidence runs out*, and every probe result goes in the incident log. There, diagnosis reproduces and reads; it writes no test into the repo and changes no application code — the red test and the fix belong to Phase 3.

**Redact as you go.** Commands, outputs and captured payloads carry tokens and personal data. Write `<REDACTED>` in their place, build every loop against environment variables rather than pasted credentials, and quote only the lines that carry the signal.

## 1. A red loop

**Build one command that goes red on this bug** — the user's exact symptom, on the actual code path — before forming any theory about the cause. With it, bisecting, testing hypotheses and probing are all mechanical. Without it, reading code produces plausible stories, not causes.

Ways to get one, roughly cheapest first:

1. **A failing test** at the highest seam that reaches the bug — the same seam the red test in Step 3 will use.
2. **A request script** (`curl`, an HTTP client) against a local or pre-production instance.
3. **A CLI run on a fixture input**, diffing its output against a known-good one.
4. **A captured artifact, replayed** — the request body, event, file or log line that triggered it, saved to disk and fed through the code path in isolation.
5. **A throwaway harness** — the smallest slice of the system (one module, real logic, faked edges) that reaches the path with one call.
6. **A property or fuzz loop** — for "sometimes wrong": many generated inputs, stop on the first that breaks.
7. **`git bisect run`** — for "it used to work": a script that builds and checks one commit, run across the range between the good and bad states.
8. **A differential run** — the same input through the old and new version (or two configs), outputs diffed.

**Never against production.** Production is evidence to read, not a loop to run: reproduce from captured artifacts, in a local or pre-production copy.

**Intermittent bugs:** the goal is a reproduction *rate*, not a clean repro. Loop the trigger, add concurrency, narrow the timing window. A bug that fails half the time is debuggable; one in a hundred is not yet — keep raising it.

**Gate — the loop is red-capable.** Name the one command, show that you ran it (output redacted), and confirm it is:

- [ ] **On the bug** — it asserts the symptom the user reported, not a nearby failure that happens to also be red. Wrong bug, wrong fix.
- [ ] **Repeatable** — the same verdict every run, or a pinned, high rate for an intermittent bug.
- [ ] **Fast** — seconds, so you can afford to run it after every change.
- [ ] **Unattended** — you run it, not the user.

**If you cannot build one,** stop here and say so: what you tried, and what would unblock it — access to the environment that reproduces it, a redacted captured artifact (a log dump, a request, a screen recording with timestamps), or permission to add temporary instrumentation. That is the lane's *cause isn't clear* exit, not a reason to guess.

## 2. Minimise

Shrink the reproduction to the smallest one that still goes red: cut one input field, caller, config value, data row or step at a time, re-running the loop after each cut, and keep only what the failure needs.

A minimal repro leaves fewer moving parts to suspect in step 3, and it *is* the red test in Step 3 of the lane — a test built from it fails for one reason only.

**Gate:** every remaining element is load-bearing — removing any one turns the loop green.

## 3. Hypotheses — several, each falsifiable

Write **three to five ranked hypotheses** before testing any. Generating one anchors on the first plausible idea, and the first plausible idea is usually the symptom's location, not its cause.

Each one states its prediction:

> If **<X>** is the cause, then **<changing Y>** turns the loop green, and **<changing Z>** makes no difference.

A hypothesis with no prediction is a hunch — sharpen it or drop it. Show the ranked list to the user when they're reachable (they often know "we changed #3 on Tuesday"); don't wait on it when they're not. In an incident, it goes in the log.

**Gate:** a ranked list, every entry with a prediction you can check.

## 4. Probe — one prediction at a time

Each probe tests one prediction from step 3, and changes one thing.

- **A debugger or REPL** where the environment allows it — one breakpoint beats ten log lines.
- **Targeted logs at the boundaries that separate the hypotheses** — never "log everything and read it." **Tag every one** with a unique prefix (`[DEBUG-a4f2]`), so cleanup is a single search.
- **Performance bugs:** logs are usually the wrong tool. Measure a baseline first (a timing harness, a profiler, the query plan), then bisect against that number.

Record what each probe eliminated as well as what it confirmed — the eliminated hypotheses are half of the evidence for the cause line.

**Gate:** one hypothesis predicted every probe correctly, and the others are each contradicted by at least one.

## 5. Close the diagnosis

- [ ] **The cause line** in the root-cause note is the surviving hypothesis, with the probe that confirmed it.
- [ ] **The red test** is the minimised repro from step 2, at the seam the lane names. If no seam reproduces the real pattern — the bug needs a chain of callers no single test can build — a shallower test gives false confidence. Write down that the seam is missing; it goes in as a follow-up, and it is a design finding in its own right.
- [ ] **After the fix,** the step 1 loop goes green on the *original*, un-minimised scenario too.
- [ ] **Every tagged log is gone** — a search for the prefix returns nothing — and throwaway harnesses are deleted or moved somewhere clearly marked.
- [ ] **The eliminated hypotheses** go in the commit or PR body, in one line each — the next person debugging nearby starts from them.

*Adapted from the `diagnosing-bugs` skill in [mattpocock/skills](https://github.com/mattpocock/skills) (MIT).*

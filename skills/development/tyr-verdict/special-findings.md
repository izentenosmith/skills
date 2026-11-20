# Special findings — read before you rule on a security finding or a weakened check

> Companion to [tyr-verdict](SKILL.md). Two kinds of finding carry extra rules. None of them changes how the merge verdict is computed; they change what counts as a refutation, what severity a confirmation gets, and how the slice is written. Source cited: TAOSSA = Dowd, McDonald & Schuh, *The Art of Software Security Assessment* (Addison-Wesley), printed page numbers.

## Security findings

A security finding is one about an authorisation gate, an isolation or tenancy boundary, an injection path, or a secret or personal value leaking into logs or responses. Three extra rules for the verdict, and one for the slice:

- **Refute only on a code path.** "No test failed" and "a scanner found nothing" are not refutations: a black-box suite misses paths that only a specific input reaches (TAOSSA pp. 11–12). REFUTED needs the guard that blocks the breaking case, named.
- **Exploitability is not severity.** A confirmed breach is a blocker even when the breaking case looks hard to reach; "an attacker would have to know the ID" is how IDs leak through a list endpoint later. Downgrade only for a stated reason that is about impact, not effort.
- **Design-layer defects go upstream.** When the defect is the design doing the wrong thing correctly — a rule another feature circumvents, a role someone can grant themselves, a fallback that skips a control — the slice fixes the symptom and the reason names [architect-deep-dive](../architect-deep-dive/SKILL.md) (and, where one exists, the threat model) as the place the decision has to be revisited.
- **The slice states the refusal and its contrast** — *"a user of another account requesting this invoice gets 404 and the invoice is unchanged; its owner still gets 200"* — so tdd's red test fails if the gate disappears or over-reaches, and the slice can't be closed by a fix with no abuse test.

## Findings about the bar itself

A finding about the bar is one where a check got weaker: a test skipped, deleted or loosened, a checker suppressed, a threshold lowered, an acceptance test edited without a brief revision. Two extra rules:

- **A green suite refutes nothing here.** The suite is green *because* the check was moved; that is the finding. REFUTED needs the reason the weakening is right — the brief revision that logged it, or the proof that the check still catches what it caught (restore it on a scratch copy, without credentials or production access, and run it).
- **The slice restores the check, then fixes what it catches.** *"`test_export_rejects_other_tenant` runs un-skipped and passes"* is the red→green target; the suppression being gone is part of it. Severity follows what the weakened check was guarding, not how small the diff line is — a skipped test on an authorisation path is a blocker.

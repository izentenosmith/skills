# Security criteria — carrying the security block

> Read this when architect-deep-dive's security trigger fired and its design has a security block.
> When it did not fire, the brief says so in one line under **Desired behavior**, and you are done.

Every item in the design's security block becomes an acceptance criterion, not a note:

- each **abuse case** → an edge-case criterion stated as a refusal ("a user cannot …", with the exact refusal the caller sees), on the template's `Abuse case:` line;
- each **authorisation rule** → criteria for the allowed actor *and* the refused ones (other actors, other tenants, anonymous), on every path to the operation, on the template's `Authorisation:` line;
- each **domain primitive** → a **Key interfaces** entry naming the type and the rule that makes a value valid, with that rule as a criterion: constructing an invalid one fails;
- each **never-logged value** → a criterion ("the reset token appears in no log line or error response").

A security decision that isn't a criterion never gets a test, and is the first thing a later change quietly undoes.

The good build plan in examples.md shows the result: a domain primitive in Key interfaces, an abuse case and an authorisation criterion in the list, and the trigger named under Desired behavior.

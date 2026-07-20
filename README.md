# Skills

A collection of repo-agnostic AI coding agent skills for taking a feature from a vague idea all the way to reviewed, tested code. Each skill lives in its own folder as a `SKILL.md` file with YAML frontmatter (`name` + `description`) that the agent loads on demand when the work matches.

Works with [Cursor](https://www.cursor.com/) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Inspired by [mattpocock/skills](https://github.com/mattpocock/skills).

## What's in here

The skills form one connected pipeline — design, specify, build, clean, then an adversarial close — plus the reference docs they lean on.

```
architect-deep-dive → agent-brief → tdd → refactor-review → devils-advocate → tyr-verdict
   (resolve design)    (the plan)   (build)  (clean up)      (assume broken)   (judge + fix loop)
```

The last three stages form a **loop**: if `tyr-verdict` returns NO-GO, its remediation slices feed back into `tdd → refactor-review → devils-advocate → tyr-verdict`, converging when the teardown finds nothing new and the verdict confirms nothing.

### Workflow skills

| Skill | What it does |
|-------|--------------|
| [architect-deep-dive](architect-deep-dive/SKILL.md) | Staff-architect design review that resolves the plan one question at a time, inferring answers from the codebase where it can. Run this first. |
| [agent-brief](agent-brief/SKILL.md) | Turns the resolved design decisions into the pure-text build plan TDD executes — ordered acceptance criteria, test seams, prior art, and scope. |
| [tdd](tdd/SKILL.md) | Test-driven development via the red-green-refactor loop (vertical slices, not horizontal). Ends by handing off to refactor-review. |
| [refactor-review](refactor-review/SKILL.md) | Reviews the current diff: names the smell, then prescribes a behavior-preserving refactoring. |
| [devils-advocate](devils-advocate/SKILL.md) | Assumes everything just built is wrong and hunts concrete evidence for each defect. Over-reports on purpose; does not fix or judge. |
| [tyr-verdict](tyr-verdict/SKILL.md) | Adjudicates the devils-advocate findings, cuts false claims, turns confirmed defects into red→green remediation slices, and issues a go/no-go verdict. |

### Reference docs

These carry no workflow of their own — the skills above link into them.

| Doc | Used by |
|-----|---------|
| [code-smells](refactor-review/code-smells.md) | refactor-review — the symptom catalog (Refactoring Guru / Fowler) |
| [refactoring-techniques](refactor-review/refactoring-techniques.md) | refactor-review — the treatment catalog |
| [good-tests](tdd/good-tests.md) | tdd — good vs. bad test examples |
| [mocking](tdd/mocking.md) | tdd — when and how to mock |
| [deep-modules](tdd/deep-modules.md) | tdd — the deep-module principle |
| [interface-design](tdd/interface-design.md) | tdd — designing for testability |

## How to use

Each skill is a folder containing a `SKILL.md` entry point and any reference docs it needs. They work with both Cursor and Claude Code.

1. **Clone the repo** somewhere on your machine.

   ```bash
   git clone https://github.com/izentenosmith/skills.git
   ```

2. **Point your agent at the skills.**
   - **Cursor** — add the cloned directory as a skills source in your Cursor settings, or symlink individual skill folders into your project's `.cursor/skills/` directory.
   - **Claude Code** — point Claude at this directory as a skills source, or symlink skill folders into your user-level skills location. Each `SKILL.md`'s frontmatter `description` tells the agent *when* the skill applies.

3. **Invoke a skill** — either let the agent trigger it automatically when your request matches the description, or call it explicitly:

   ```
   /agent-brief
   /tdd
   /refactor-review
   /devils-advocate
   /tyr-verdict
   ```

You don't have to run the whole pipeline. Any skill works on its own — but the descriptions note where running an earlier skill first gives better results (e.g. `agent-brief` after `architect-deep-dive`, or `tyr-verdict` after `devils-advocate`).

## Conventions

- **One skill per folder.** Each folder contains a `SKILL.md` (the workflow) and any companion reference docs it needs.
- **Every `SKILL.md` carries frontmatter** (`name`, `description`) so the agent can decide relevance.
- **Skills cross-link** with relative Markdown links to compose into pipelines.
- **Behavioral, not procedural** — skills describe *what* to achieve and let the agent figure out *how* against the live codebase. No hard-coded file paths or line numbers.

## License

[MIT](LICENSE) — free to use, modify, and distribute as is.

# Skills

A collection of repo-agnostic AI coding agent skills for taking a feature from a vague idea all the way to reviewed, tested code. Each skill lives in its own folder as a `SKILL.md` file with YAML frontmatter (`name` + `description`) that the agent loads on demand when the work matches.

Works with [Cursor](https://www.cursor.com/) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Inspired by [mattpocock/skills](https://github.com/mattpocock/skills).

## What's in here

The skills form one connected pipeline — design, specify, build, review — plus the reference docs they lean on.

```
architect-deep-dive  →  product-requirement-document  →  agent-brief  →  tdd  →  refactor-review
   (resolve design)        (write & publish the PRD)        (the spec)    (build)   (clean up)
```

### Workflow skills

| Skill | What it does |
|-------|--------------|
| [architect-deep-dive](architect-deep-dive/SKILL.md) | Staff-architect design review that resolves the plan one question at a time, inferring answers from the codebase where it can. Run this first. |
| [product-requirement-document](product-requirement-document/SKILL.md) | Synthesizes the conversation into a PRD and publishes it to the issue tracker with a `ready-for-agent` label. Best run right after the deep dive. |
| [agent-brief](agent-brief/SKILL.md) | Writes the durable, behavioral spec an AFK agent works from — posted as a comment when an issue hits `ready-for-agent`. |
| [tdd](tdd/SKILL.md) | Test-driven development via the red-green-refactor loop (vertical slices, not horizontal). Ends by handing off to refactor-review. |
| [refactor-review](refactor-review/SKILL.md) | Reviews the current diff: names the smell, then prescribes a behavior-preserving refactoring. |

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
   /tdd
   /refactor-review
   /product-requirement-document
   ```

You don't have to run the whole pipeline. Any skill works on its own — but the descriptions note where running an earlier skill first gives better results (e.g. `product-requirement-document` after `architect-deep-dive`).

## Conventions

- **One skill per folder.** Each folder contains a `SKILL.md` (the workflow) and any companion reference docs it needs.
- **Every `SKILL.md` carries frontmatter** (`name`, `description`) so the agent can decide relevance.
- **Skills cross-link** with relative Markdown links to compose into pipelines.
- **Behavioral, not procedural** — skills describe *what* to achieve and let the agent figure out *how* against the live codebase. No hard-coded file paths or line numbers.

## License

[MIT](LICENSE) — free to use, modify, and distribute as is.

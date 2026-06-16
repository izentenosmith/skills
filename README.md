# Skills

A collection of [Claude Code](https://claude.com/claude-code) skills for taking a feature from a vague idea all the way to reviewed, tested code. Each skill is a single Markdown file with YAML frontmatter (`name` + `description`) that Claude loads on demand when the work matches.

Inspired by [mattpocock/skills](https://github.com/mattpocock/skills).

## What's in here

The skills form one connected pipeline — design, specify, build, review — plus the reference docs they lean on.

```
architect-deep-dive  →  product-requirement-document  →  agent-brief  →  tdd  →  code-review
   (resolve design)        (write & publish the PRD)        (the spec)    (build)   (clean up)
```

### Workflow skills

| Skill | What it does |
|-------|--------------|
| [architect-deep-dive](architect-deep-dive.md) | Staff-architect design review that resolves the plan one question at a time, inferring answers from the codebase where it can. Run this first. |
| [product-requirement-document](product-requirement-document.md) | Synthesizes the conversation into a PRD and publishes it to the issue tracker with a `ready-for-agent` label. Best run right after the deep dive. |
| [agent-brief](agent-brief.md) | Writes the durable, behavioral spec an AFK agent works from — posted as a comment when an issue hits `ready-for-agent`. |
| [tdd](tdd.md) | Test-driven development via the red-green-refactor loop (vertical slices, not horizontal). Ends by handing off to code review. |
| [code-review](code-review.md) | Reviews the current diff: names the smell, then prescribes a behavior-preserving refactoring. |

### Reference docs

These carry no workflow of their own — the skills above link into them.

| Doc | Used by |
|-----|---------|
| [code-smells](code-smells.md) | code-review — the symptom catalog (Refactoring Guru / Fowler) |
| [refactoring-techniques](refactoring-techniques.md) | code-review — the treatment catalog |
| [tests](tests.md) | tdd — good vs. bad test examples |
| [mocking](mocking.md) | tdd — when and how to mock |
| [deep-modules](deep-modules.md) | tdd — the deep-module principle |
| [interface-design](interface-design.md) | tdd — designing for testability |

## How to use

These are [Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills). To make them available:

1. **Clone the repo** somewhere on your machine.

   ```bash
   git clone https://github.com/izentenosmith/skills.git
   ```

2. **Make Claude Code aware of them.** Point Claude at this directory (e.g. as a plugin/skills source, or by symlinking the files into your project's or user-level skills location). Each `.md` file's frontmatter `description` tells Claude *when* the skill applies.

3. **Invoke a skill** — either let Claude trigger it automatically when your request matches the description, or call it explicitly:

   ```
   /tdd
   /code-review
   /product-requirement-document
   ```

You don't have to run the whole pipeline. Any skill works on its own — but the descriptions note where running an earlier skill first gives better results (e.g. `product-requirement-document` after `architect-deep-dive`).

## Conventions

- **One concept per file.** Workflow skills describe a process; reference docs describe knowledge.
- **Every file carries frontmatter** (`name`, `description`) so Claude can decide relevance.
- **Skills cross-link** with relative Markdown links to compose into pipelines.
- **Behavioral, not procedural** — skills describe *what* to achieve and let Claude figure out *how* against the live codebase. No hard-coded file paths or line numbers.

## License

[MIT](LICENSE) — free to use, modify, and distribute as is.

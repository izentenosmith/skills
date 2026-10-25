# containers

Two skills for packaging a service to run: an image, then the stack around it.

```
dockerfile → docker-compose
 (the image)  (the stack)
```

## The skills

| Skill | What it does |
|-------|--------------|
| [dockerfile](dockerfile/SKILL.md) | Reads the stack off the repo, writes a multi-stage production Dockerfile — pinned base, non-root runtime, cache-correct layer order — and generates or repairs the `.dockerignore` that defines its build context. Verifies by building and running, not by reading. |
| [docker-compose](docker-compose/SKILL.md) | Detects the services the code actually connects to, wires them with named volumes, an isolated network and real health gates, and ships a documented `.env.example` plus a dev override. Verifies from cold, twice. |

## How to use them

Install both from the root of the repo you're working in:

```bash
npx skills add izentenosmith/skills --skill dockerfile docker-compose
```

Or one at a time:

| Skill | Install |
|---|---|
| dockerfile | `npx skills add izentenosmith/skills --skill dockerfile` |
| docker-compose | `npx skills add izentenosmith/skills --skill docker-compose` |

Flags (`-a`, `-g`, `-y`) are in the [root README](../../README.md#install-with-npx).

Or **copy the folders you want into the repo you're working in**, alongside wherever that repo keeps its agent skills. Each folder is self-contained — `SKILL.md` plus its reference docs — so one folder is a complete install of one skill.

Then either let the agent trigger the skill when your request matches its `description`, or call it by name:

```
/dockerfile   /docker-compose
```

## Run `dockerfile` first

Compose orchestrates images; it cannot repair one. Most "compose is broken" reports turn out to be an image that doesn't start, doesn't answer its healthcheck, or dies on `SIGTERM` — and no amount of compose configuration fixes any of those.

A service whose image is already correct gets composed in minutes. `docker-compose` works fine on third-party images alone (a database for local development, say) and does not require the other skill to have run.

## What each one is calibrated for

Both take a **greenfield / repair / audit** stance up front, because the three are different jobs:

- **Greenfield** — nothing exists; you're choosing the whole shape.
- **Repair** — something exists and is wrong. Both skills require naming the specific defect before editing, because rewriting a Dockerfile or compose file that currently works is the most expensive way to introduce a regression into something that was shipping.
- **Audit** — report what's wrong, change nothing.

Both also stop deliberately. There is always another 8MB and another compose setting; **an optimization that doesn't reduce build time, image size, or attack surface by an amount someone would notice is a diff for its own sake.** Compose in particular is a local development tool, and hardening it into a deployment manifest produces a bad manifest and a confusing dev environment at the same time.

## Reference docs

| Doc | Used by |
|-----|---------|
| [optimization](dockerfile/optimization.md) | dockerfile — base image trade-offs, layer order, cache mounts, secrets, signals and PID 1 |
| [dockerignore](dockerfile/dockerignore.md) | dockerfile — what to exclude, per-stack, and what each exclusion actually buys |
| [service-catalog](docker-compose/service-catalog.md) | docker-compose — per-service image, readiness probe, volume path, connection string, and the trap specific to each |
| [environments](docker-compose/environments.md) | docker-compose — override files, merge rules, `.env.example`, secrets, where the dev/prod line sits |

## Measured

`docker-compose` has an eval fixture and a scored assertion set in [`../evals/`](../../evals/README.md) — a Flask service with RQ queues on Redis, a stale `ELASTICSEARCH_URL` pointing at a service the code no longer uses, and a migration step that must finish before the API starts. The assertions discriminate: a naive compose file scores 6/6 on capability and **0/9** on the assertions that test what this skill instructs. **First run (n=1): 0.89 against 0.67 for no skill**; the miss was a connection string that kept `localhost`.

`dockerfile` has one too (eval 28): a TypeScript service whose Dockerfile ships but runs as root on `node:latest`, copies source before installing, bakes a key into `ENV`, exposes a port the code doesn't listen on, and builds on Apple Silicon for an amd64 cluster, beside a curated `.dockerignore` a repair must extend rather than replace. The Dockerfile is parsed stage by stage and the `.dockerignore` evaluated with Docker's matching rules; nothing is built. Reference, do-nothing and plausible-but-wrong controls separate as intended (`python3 evals/controls/make_controls.py --only 28`). **First run (n=1): 0.79 against 0.79 for no skill** — no better than none, and it quoted the planted key in its rotation warning. The weakest result in the repo.

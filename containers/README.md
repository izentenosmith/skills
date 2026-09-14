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

**Copy the folders you want into the repo you're working in**, alongside wherever that repo keeps its agent skills. Each folder is self-contained — `SKILL.md` plus its reference docs — so one folder is a complete install of one skill.

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

## Measured, partly

`docker-compose` has an eval fixture and a scored assertion set in [`../evals/`](../evals/README.md) — a Flask service with RQ queues on Redis, a stale `ELASTICSEARCH_URL` pointing at a service the code no longer uses, and a migration step that must finish before the API starts. The assertions discriminate: a naive compose file scores 6/6 on capability and **0/9** on the assertions that test what this skill instructs. **No with-skill run has been scored yet**, so there is no number for the skill itself.

`dockerfile` has no eval.

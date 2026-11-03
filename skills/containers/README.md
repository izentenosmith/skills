# containers

Five skills: two for packaging a service to run — an image, then the stack around it — and three for containers once they're out there: how securely they run, why one isn't running, and the Swarm cluster some of them run on.

```
dockerfile → docker-compose        container-hardening · container-debug · docker-swarm
 (the image)  (the stack)          (how it runs · why it doesn't · the Swarm around it)
```

## The skills

| Skill | What it does |
|-------|--------------|
| [dockerfile](dockerfile/SKILL.md) | Reads the stack off the repo, writes a multi-stage production Dockerfile — pinned base, non-root runtime, cache-correct layer order — and generates or repairs the `.dockerignore` that defines its build context. Verifies by building and running, not by reading. |
| [docker-compose](docker-compose/SKILL.md) | Detects the services the code actually connects to, wires them with named volumes, an isolated network and real health gates, and ships a documented `.env.example` plus a dev override. Verifies from cold, twice. |
| [container-hardening](container-hardening/SKILL.md) | Reviews how containers run — Compose, Kubernetes, Swarm or `docker run` — and the image supply chain, against the principles every finding cites and a scored rubric: privileged mode, the Docker socket, host namespaces and mounts, root and capabilities, seccomp and LSMs, read-only roots, limits, exposed ports, secrets, scanning and signing. Review scores 0–10 with the shared formula and a gate; Harden applies fixes to the repo's config and proves the workload still runs. |
| [container-debug](container-debug/SKILL.md) | For a container that won't start, stay up or connect — Docker, Compose, Swarm or Kubernetes. Captures the evidence before a restart destroys it, reads the runtime's own record (exit code, `OOMKilled`, restart count, health log, events), matches the symptom against the failures that only exist in containers (`localhost` meaning the container, CRLF entrypoints, wrong architecture, write paths, signals), proves one hypothesis at a time, and routes the fix to the skill that owns it. Read-only in production; outages go to incident-fix. |
| [docker-swarm](docker-swarm/SKILL.md) | Reviews or designs a Docker Swarm mode cluster and the stack files `docker stack deploy` reads, against the principles every finding cites and a scored rubric: manager count and quorum, autolock, backups and certificate rotation; `update_config`, `rollback_config`, restart policy and the healthcheck as the rollout gate; stateful services and node-local volumes; overlays, encryption and the routing mesh; secrets and configs; reservations and placement; and the keys stack deploy ignores. Opens with a fit verdict — Swarm, Compose on a VM, or Kubernetes. Review scores 0–10 with the shared formula; Design lays out the cluster and a stack file validated with `docker stack config`. Read-only: it never deploys, updates, scales or removes. |

## How to use them

Install all five from the root of the repo you're working in:

```bash
npx skills add izentenosmith/skills --skill dockerfile docker-compose container-hardening container-debug docker-swarm
```

Or one at a time:

| Skill | Install |
|---|---|
| dockerfile | `npx skills add izentenosmith/skills --skill dockerfile` |
| docker-compose | `npx skills add izentenosmith/skills --skill docker-compose` |
| container-hardening | `npx skills add izentenosmith/skills --skill container-hardening` |
| container-debug | `npx skills add izentenosmith/skills --skill container-debug` |
| docker-swarm | `npx skills add izentenosmith/skills --skill docker-swarm` |

The repo is private: you need read access and GitHub auth first. That setup, and the flags (`-a`, `-g`, `-y`), are in the [root README](../../README.md#install-with-npx).

Or **copy the folders you want into the repo you're working in**, alongside wherever that repo keeps its agent skills. Each folder is self-contained — `SKILL.md` plus its reference docs — so one folder is a complete install of one skill.

Then either let the agent trigger the skill when your request matches its `description`, or call it by name:

```
/dockerfile   /docker-compose   /container-hardening   /container-debug   /docker-swarm
```

## Run `dockerfile` first

Compose orchestrates images; it cannot repair one. Most "compose is broken" reports turn out to be an image that doesn't start, doesn't answer its healthcheck, or dies on `SIGTERM` — and no amount of compose configuration fixes any of those.

A service whose image is already correct gets composed in minutes. `docker-compose` works fine on third-party images alone (a database for local development, say) and does not require the other skill to have run.

## Where `container-hardening` sits

It isn't a third step after compose — it reviews wherever containers actually run: a Compose file deployed to a VM, Kubernetes manifests, a Swarm stack, `docker run` in a script. It splits work with the other two along clear lines: **an image finding (no `USER`, setuid binaries, a secret in a layer, an unpinned base) is reported by container-hardening and fixed by dockerfile**; a **dev Compose stack** is checked only for what hurts the laptop (the Docker socket, `privileged`, ports on every interface), and production-grade settings go in a separate file rather than into the dev experience docker-compose built.

It uses the same 0–10 formula, caps and gate structure as the database, networking, Terraform and pipeline reviews, so a score means the same thing across the repo.

## Where `container-debug` sits

It's the one you call when something built with the others misbehaves, and it hands the fix back: an image defect to dockerfile, wiring to docker-compose, a security setting to container-hardening, an application bug to [hotfix](../operations/hotfix/SKILL.md). A **production outage** is an incident first — [incident-fix](../operations/incident-fix/SKILL.md) contains, then uses container-debug's tables to gather evidence.

## Where `docker-swarm` sits

Swarm is maintained and stable, and in 2026 it is a niche choice: the skill opens by saying whether it fits (one host → Compose on a VM with container-hardening; a small cluster and a small team → Swarm; autoscaling, many teams, admission policy or operators → Kubernetes). It reads the same file format as docker-compose and treats it as a different contract — docker-compose's [environments.md](docker-compose/environments.md#if-the-same-file-goes-to-docker-stack-deploy) lists what stack deploy ignores, and a team on Swarm keeps a separate stack file. Each service's container security goes to container-hardening; a missing image healthcheck goes to dockerfile, because Swarm gates every rolling update on it.

## What dockerfile and docker-compose are calibrated for

Both take a **greenfield / repair / audit** stance up front, because the three are different jobs:

- **Greenfield** — nothing exists; you're choosing the whole shape.
- **Repair** — something exists and is wrong. Both skills require naming the specific defect before editing, because rewriting a Dockerfile or compose file that currently works is the most expensive way to introduce a regression into something that was shipping.
- **Audit** — report what's wrong, change nothing.

Both also stop deliberately. There is always another 8MB and another compose setting; **an optimization that doesn't reduce build time, image size, or attack surface by an amount someone would notice is a diff for its own sake.** Compose in particular is a local development tool, and hardening it into a deployment manifest produces a bad manifest and a confusing dev environment at the same time.

## Reference docs

| Doc | Used by |
|-----|---------|
| [optimization](dockerfile/optimization.md) | dockerfile — base image trade-offs, pinning that keeps moving, what the cache keys on, cache mounts, secrets, non-root and setuid, signals and PID 1, ENTRYPOINT vs CMD, healthchecks, logging, labels, debugging a failed build, SBOM and signing |
| [dockerignore](dockerfile/dockerignore.md) | dockerfile — what to exclude, per-stack, what each exclusion actually buys, and why every pattern is anchored at the context root |
| [service-catalog](docker-compose/service-catalog.md) | docker-compose — per-service image, readiness probe, volume path, connection string, and the trap specific to each; loopback ports and the Docker socket |
| [environments](docker-compose/environments.md) | docker-compose — override files, merge rules, `.env.example`, secrets under Compose, Swarm and Kubernetes, what `docker stack deploy` ignores, where the dev/prod line sits |
| [theory](container-hardening/theory.md) | container-hardening — the principles every finding cites (C1–C13): the shared kernel, least privilege, host interfaces as root, secrets, supply chain |
| [controls](container-hardening/controls.md) | container-hardening — eight domains plus the host: what good looks like, each anti-pattern's what / why / detect / fix / cost / severity, the scored checklists |
| [platforms](container-hardening/platforms.md) | container-hardening — every control as a `docker run` flag, Compose key, Kubernetes field and Swarm option; the `docker inspect` templates that prove it; grep signals; what each scanner sees |
| [scoring](container-hardening/scoring.md) | container-hardening — severity anchors and chains, confidence, the 0–10 formula, the gate, templates |
| [symptoms](container-debug/symptoms.md) | container-debug — exit codes (137 vs OOM, 127 vs 255), and each symptom — won't start, won't stay up, can't connect, unhealthy, slow — with its causes and the probe that tells them apart |
| [toolkit](container-debug/toolkit.md) | container-debug — the same questions in Docker, Compose, Swarm and Kubernetes; inspect templates that don't print secrets; a shell for images with none; keeping evidence |
| [theory](docker-swarm/theory.md) | docker-swarm — the principles every finding cites (S1–S12): desired state, quorum, effective settings, rollouts that detect and undo, node-local state, the routing mesh, overlay encryption, reservations, immutable secrets, the control plane |
| [controls](docker-swarm/controls.md) | docker-swarm — cluster, rollout, state, network, secrets, scheduling, stack file: what good looks like, anti-patterns with what / why / detect / fix / severity, the scored checklists |
| [runbook](docker-swarm/runbook.md) | docker-swarm — the read-only commands and what to read in them; failure modes (quorum loss, lost unlock key, pending tasks, paused updates, lost data after a drain) with their recovery; drills before go-live; the stack file skeleton |
| [scoring](docker-swarm/scoring.md) | docker-swarm — severity anchors and chains, confidence, the 0–10 formula, the go-live gate, templates |

The references were reviewed against *Container Security* (Rice, 2nd ed.), *Docker in Action* (Nickoloff & Kuenzli, 2nd ed.), *Docker: Up & Running* (Kane & Matthias, 2nd ed.), *Docker Deep Dive* (Poulton), *Docker in Practice* ch. 3, *Container Security 101* (Practical DevSecOps), and two Swarm course decks. Advice those sources give that current Docker has superseded — the legacy builder, Compose v1, `--link`, data-volume containers, Docker Content Trust — was left out on purpose.

## Measured

`docker-compose` has an eval fixture and a scored assertion set in [`../evals/`](../../evals/README.md) — a Flask service with RQ queues on Redis, a stale `ELASTICSEARCH_URL` pointing at a service the code no longer uses, and a migration step that must finish before the API starts. The assertions discriminate: a naive compose file scores 6/6 on capability and **0/9** on the assertions that test what this skill instructs. **Scored at n=3 (2026-11-03): 1.00 against 0.78 for no skill.** The first run's one miss (0.89 against 0.67) was a grader false negative, fixed: it failed the `localhost` Meilisearch healthcheck that this skill's service catalog prescribes.

`dockerfile` has one too (eval 28): a TypeScript service whose Dockerfile ships but runs as root on `node:latest`, copies source before installing, bakes a key into `ENV`, exposes a port the code doesn't listen on, and builds on Apple Silicon for an amd64 cluster, beside a curated `.dockerignore` a repair must extend rather than replace. The pod also sets `runAsNonRoot: true`, so the user must be numeric. The Dockerfile is parsed stage by stage and the `.dockerignore` evaluated with Docker's matching rules; the grader builds nothing. Reference, do-nothing and plausible-but-wrong controls separate as intended (`python3 evals/controls/make_controls.py --only 28`). **Scored at n=3 (2026-11-03): 1.00 against 0.83 for no skill.** The first run tied at 0.79, because most of its assertions tested what any competent repair does. The eval now also tests what this skill specifically instructs: a numeric uid, code left root-owned, the digest's updater named, and a cache check by content, not `touch`. The gain is in three things the bare agent skipped in both of its runs: it quoted the planted key, it listed checks without their commands, and it never said nothing bumps the digest.

`container-hardening` has one too (eval 35): a Compose file that is the production deploy, with a Watchtower socket mount the README calls read-only, a Postgres port the README says `ufw` blocks, a privileged worker that only needs `/dev/dri`, a committed live key, and a Kubernetes pod hardened in every way but its seccomp profile — beside a proxy service that is the hardened template. Reference, do-nothing and plausible-but-wrong controls separate as intended (`python3 evals/controls/make_controls.py --only 35`). **Scored at n=3 (2026-11-03): 1.00 against 0.57 for no skill.** The bare review quoted the live key, called the pod's missing seccomp profile a small gap, and had no score, gate or needs-access flags.

`container-debug` has one (eval 36): a staging stack broken three ways, with only captured output — a worker the README says is "crashing" that `inspect` shows `OOMKilled: true` against a 256 MiB limit and a measured 418 MiB working set; an api whose Redis "is slow to start" but whose `REDIS_URL` is `localhost`; a migration whose entrypoint "is definitely in the image" and exits 255 because of CRLF line endings; and a database password sitting in the captured `inspect` output. Controls separate as intended (`--only 36`). **Scored at n=3 (2026-11-03): 1.00 against 0.82 for no skill.** A bare agent diagnoses all three symptoms. It misses the exposed password in the capture and the root-cause notes.

`docker-swarm` has one too (eval 37): a five-node cluster going live with **two managers** the README calls highly available, Postgres at `replicas: 2` on a local volume with no placement constraint, a README that relies on `depends_on` to order startup, a `.env` the CI deploy script never exports (so `docker stack config` renders the API image with an empty tag), an API with no healthcheck under the default `pause`/`stop-first` update config, an nginx edge that rate-limits per client IP behind the routing mesh, and a committed `secrets: file:` source — beside a worker service that is the template. Reference, do-nothing and plausible-but-wrong controls separate as intended (`python3 evals/controls/make_controls.py --only 37`). **Scored at n=3 (2026-11-03): 1.00 against 0.75 for no skill.** A bare review finds every planted defect but gives no score, no needs-access flags and no verdict on whether Swarm fits.

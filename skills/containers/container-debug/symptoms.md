# Symptoms — what each one usually is, and the command that tells the causes apart

**Contents:** Exit codes · Won't start · Won't stay up · Can't connect · Unhealthy · Slow, or different from outside a container

The table behind [SKILL.md](SKILL.md) Step 2. Each row lists causes **most common first** and the
**discriminating probe**: the one command whose output separates them. Read-only unless marked. Commands
use Docker; [toolkit.md](toolkit.md) has the Compose, Swarm and Kubernetes equivalents.

Sources: *Docker: Up & Running* 2nd ed. ch. 5–7, 11 (debugging, logs, events, resource limits);
*Docker in Action* 2nd ed. ch. 2, 4–6, 8 (networking, volumes, users, entrypoints); *Docker Deep Dive*
ch. 8–13; *Container Security* 2nd ed. ch. 4, 8, 11; *Docker in Practice* 2nd ed. ch. 3 (commit as a
forensic snapshot). Current-practice items (BuildKit, `kubectl debug`, cgroup v2) are not from the books.

---

## Exit codes

| Code | Signal | Usually | Probe |
|---|---|---|---|
| 0 | — | The main process finished: a server that forks into the background (`nginx` without `daemon off`, `service x start`), a shell-form `CMD` running a script that returns, or a one-shot job doing its job | `docker inspect -f '{{json .Config.Entrypoint}} {{json .Config.Cmd}}'` — what PID 1 actually is |
| 1 | — | The app failed and said so — a config error, a missing env var, an unreachable dependency at boot | `docker logs --tail 50` — the last lines |
| 2 | — | Misuse: bad CLI flags, a shell syntax error in an entrypoint script | logs; `sh -n entrypoint.sh` |
| 126 | — | Found but not executable: missing `+x`, mounted `noexec`, a directory at that path | `docker run --rm --entrypoint ls <img> -l <path>` |
| 127 | — | Not found, **when a shell ran the command**: wrong path or stage; the interpreter in `#!` not found — a CRLF line ending makes it look for `/bin/sh\r`; a glibc binary on musl (alpine) whose loader doesn't exist | `od -c <script> \| head -2` (look for `\r`); `file <binary>`; `ldd` in a glibc image |
| 255 | — | The runtime couldn't exec an **exec-form** entrypoint at all: `exec /app/entrypoint.sh: no such file or directory` on a file that exists (CRLF on its `#!` line, a missing loader), or `exec format error` (wrong architecture). `.State.Error` is often empty; the message is the container's only log line | `docker logs <c>`; `od -c <script> \| head -1`; the image's architecture |
| 134 | ABRT (6) | The process aborted itself: an assertion, a native-library error, a JVM fatal error | logs; a core or `hs_err` file in the writable layer (`docker diff`) |
| 137 | KILL (9) | **OOM-killed** (`.State.OOMKilled=true`) · **`docker stop` timed out** after the grace period · an orchestrator killed it (liveness probe, eviction, `docker kill`) | `docker inspect -f '{{.State.OOMKilled}}'`; `docker events --since 1h --until "$(date +%s)" --filter container=<c>` (`oom` vs `kill`/`stop`); Kubernetes `Last State: Terminated, Reason: OOMKilled` |
| 139 | SEGV (11) | A crash in native code: a library built for another libc or CPU feature set, an emulated (QEMU) binary, a real bug | the image's architecture vs the host's; does it crash under `--platform` emulation only? |
| 143 | TERM (15) | A normal stop that the app handled — expected on `docker stop`, unexpected in a crash loop (something keeps stopping it: a liveness probe, an updater, a deploy) | `docker events` for who sent `stop`/`kill` |

**Note on 137.** Without `OOMKilled=true`, a 137 is not a memory problem. A 137 that arrives exactly
`stop_grace_period` (default 10 s) after a `stop` event means the app ignored `SIGTERM` — shell-form
`CMD`, an entrypoint script without `exec`, or a PID 1 that never installed a handler. That's the
image's bug (dockerfile skill, "Signals and PID 1").

---

## Won't start

| Observed | Causes | Probe |
|---|---|---|
| `exec format error` | Image architecture ≠ host (an arm64 image built on Apple Silicon running on amd64, or the reverse) · a script with no `#!` line | `docker image inspect -f '{{.Os}}/{{.Architecture}}' <img>` vs `uname -m`; `head -c 2 <script>` should be `#!` |
| `exec: "x": executable file not found in $PATH` | The binary isn't in this stage (multi-stage `COPY --from` missed it) · `PATH` differs · a typo in exec-form `CMD` | `docker run --rm --entrypoint sh <img> -c 'command -v x; echo $PATH'` |
| `no such file or directory` on a file that exists | **CRLF in the script's `#!` line** · a binary's dynamic loader missing (glibc binary on alpine) · a symlink to a path not in the image | `od -c <script> \| head -1`; `file <binary>` |
| `permission denied` at start | Script not executable · non-root user can't read the binary · `noexec` tmpfs or volume over the path | `ls -l` in the image; `docker inspect` mounts |
| `bind: address already in use` (host) | Another process or container already publishes that host port | `ss -ltnp \| grep :<port>` on the host; `docker ps --format '{{.Names}} {{.Ports}}'` |
| `bind: permission denied` (in container) | Non-root binding a port below 1024 on a runtime that doesn't allow it (host network, some Kubernetes runtimes) | Is it `--network host`? Use a high port |
| Container never created | Image pull failure (auth, tag, platform not in the manifest) · a mount source that doesn't exist · an invalid config | `docker compose up` output; `docker pull <img>`; `docker buildx imagetools inspect <img>` for platforms |
| Kubernetes `CreateContainerConfigError` | A referenced Secret or ConfigMap key missing · `runAsNonRoot` with a **named** `USER` it can't verify | `kubectl describe pod` Events |
| Kubernetes `ImagePullBackOff` | Tag or registry wrong, no pull secret, the platform missing from the manifest list | `kubectl describe pod` Events |

---

## Won't stay up (exits, restart loop, CrashLoopBackOff)

| Observed | Causes | Probe |
|---|---|---|
| Exits `0` immediately | The process daemonised or the command finished (see exit 0 above) | What PID 1 is: `.Config.Entrypoint` + `.Config.Cmd` |
| Exits `1` within seconds | Missing config or secret · a dependency not reachable at boot and no retry · a migration failing | `docker logs`; is every required env var present by **name**? |
| Exits after a fixed delay, every time | A liveness probe or healthcheck killing a slow starter (no `start_period`/`initialDelaySeconds`) · a startup timeout in the app | `docker inspect -f '{{json .State.Health}}'`; Kubernetes Events (`Liveness probe failed`) |
| `137` with `OOMKilled=true` | The limit is below the working set · a leak · a JVM/runtime sizing its heap from the host, not the limit | `docker stats --no-stream` while it runs; the limit `{{.HostConfig.Memory}}`; JVM: `-XX:MaxRAMPercentage` |
| `Restarting`, and `exec` refused | The restart policy keeps it cycling; there's nothing to exec into between attempts | `docker run --rm -it --entrypoint sh <img>` or `docker compose run --rm --entrypoint sh <svc>` — a fresh container you control |
| Exits only under `--read-only` | The app writes somewhere not listed as a volume or tmpfs | Run writable, exercise it, `docker diff <c>` — the `A`/`C` lines are the write paths |
| Exits only as non-root | It writes to a path owned by root (often the `WORKDIR`, or a volume created by root) | `docker run --rm --entrypoint sh <img> -c 'id; ls -ld <path>'` |
| Exits only with capabilities dropped | It needs one capability by name (`NET_BIND_SERVICE`, `CHOWN`, `SETUID`) | The error message names the operation; add back that one, never `SYS_ADMIN` |
| One-shot service (migration) `Exited (1)`, app never starts | The app waits on `service_completed_successfully` and the job failed | `docker compose ps -a` (without `-a` the failed job isn't listed); its logs |

---

## Can't connect

| Observed | Causes | Probe |
|---|---|---|
| `connection refused` to `localhost:<port>` from a container | **`localhost` is the container itself** — the target is another container | The connection string; use the service name (`redis:6379`) |
| `connection refused` to `<service>:<port>` | Target up but not listening yet (no health gate, no retry) · listening on `127.0.0.1` inside its container instead of `0.0.0.0` · wrong port (the published one instead of the container port) | In the target's namespace: `ss -ltn` (`127.0.0.1:8000` vs `0.0.0.0:8000`); `docker inspect` health |
| `no such host` / `Name or service not known` / `lookup X on 127.0.0.11` | The two containers share no network · the target isn't running (no DNS record) · using the default `bridge` network, which has no name resolution · a typo | `docker inspect -f '{{json .NetworkSettings.Networks}}' <c>` for both; `getent hosts <name>` from inside or from a sidecar |
| Works from the host, not from another container | The host uses the **published** port on `localhost`; containers use the service name and the **container** port | Compare `ports:` with the connection string |
| Works between containers, not from the host | The port isn't published, or is published on `127.0.0.1` and the client is elsewhere · a host firewall on the client's path | `docker port <c>`; `{{json .NetworkSettings.Ports}}` |
| Reachable from the internet when it shouldn't be | Published on `0.0.0.0` — and Docker's iptables rules bypass `ufw`/`firewalld` | `{{json .NetworkSettings.Ports}}` (`HostIp`); hand to [container-hardening](../container-hardening/SKILL.md) |
| Outbound calls fail (DNS or TLS) | No CA certificates in the image (`scratch`, some minimal bases) → TLS errors · `/etc/resolv.conf` copied from a host using a local resolver (`127.0.0.53`) unreachable from the container · an `internal: true` network · a corporate proxy not passed in | `cat /etc/resolv.conf` inside; `ls /etc/ssl/certs`; `{{.HostConfig.Dns}}` |
| Intermittent timeouts under load | Connection pool exhausted · Swarm/K8s VIP load balancing per connection with keep-alives pinning to one replica · conntrack table full on the host | app metrics; `docker stats`; host `dmesg` for conntrack |

---

## Unhealthy

| Observed | Causes | Probe |
|---|---|---|
| `unhealthy` but serving | The healthcheck uses a tool the image lacks (`curl` on slim/distroless) · checks the wrong port or path · exits with a code other than 0/1 | `docker inspect -f '{{json .State.Health}}' \| jq` — `Log[].Output` holds the probe's own output |
| `unhealthy` during startup only | No `start_period`, so slow boots count against `retries` | the timestamps in `Health.Log` vs `StartedAt` |
| `unhealthy` and nothing happens | Plain Docker acts on nothing but exit; only an orchestrator replaces unhealthy containers | expected behaviour — `restart:` reacts to exit, not health |
| Healthy, but dependents start too early | `depends_on` without `condition: service_healthy` waits only for *started* · the healthcheck tests liveness, not readiness (a port open before the DB accepts queries) | the compose file; the probe command |

---

## Slow, or different from outside a container

| Observed | Causes | Probe |
|---|---|---|
| Builds or runs several times slower on a Mac | The image is for the other architecture and runs under QEMU emulation | `{{.Architecture}}` vs host |
| Bind-mounted project very slow (macOS, Windows) | File sharing through the VM; huge `node_modules` trees over a bind mount | use `develop.watch` or a volume for dependency directories |
| CPU-throttled while the host is idle | A CPU quota (`--cpus`, `limits.cpu`) reached during bursts | `cat /sys/fs/cgroup/cpu.stat` inside (`nr_throttled`, cgroup v2) |
| Disk full on the host | Unrotated `json-file` logs · writes to the container layer · dangling images and volumes | `docker system df`; `du` under `/var/lib/docker/containers/*/*-json.log` |
| Old code after a rebuild | Compose reused an **anonymous volume** masking the new image's files (`/app/node_modules`) · the image wasn't actually rebuilt or re-pulled · `restart` doesn't re-read the compose file | `docker compose up --build -V`; `docker inspect -f '{{.Image}}'` vs the newest image ID |
| Data gone after `down`/`up` | No named volume: the data was in an anonymous volume now orphaned | `docker volume ls -f dangling=true` — recover before anyone prunes |
| Time, locale or timezone wrong | No `tzdata` in the image; `TZ` unset | `date` inside; `ls /usr/share/zoneinfo` |
| Zombie processes, PIDS climbing | PID 1 doesn't reap children | `docker stats` PIDS column; `docker top <c>`; add an init (`init: true`) |
| `docker stop` takes 10 s | `SIGTERM` never reaches the app (shell form, script without `exec`, no handler on PID 1) | `time docker stop <c>`; `.Config.Cmd` form |

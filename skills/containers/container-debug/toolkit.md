# Toolkit — reading a container without disturbing it

The commands behind [SKILL.md](SKILL.md) Steps 1 and 3, grouped by the question they answer, with
what each can't see. **Read-only** unless the row says otherwise; anything marked ⚠️ changes state —
locally that's fine once the evidence is captured, in production it needs the user's yes.

---

## Per platform: the same questions

| Question | Docker | Compose | Swarm | Kubernetes |
|---|---|---|---|---|
| What's running, what exited | `docker ps -a` | `docker compose ps -a` | `docker service ps --no-trunc <svc>` | `kubectl get pods -o wide` |
| Why it stopped | `docker inspect -f '{{json .State}}' <c>` | same, on the container name | the ERROR column above; `docker inspect <task-container>` on its node | `kubectl describe pod <p>` → Last State |
| What it said | `docker logs --timestamps --tail 200 <c>` | `docker compose logs --timestamps --tail 200 <svc>` | `docker service logs --timestamps <svc>` | `kubectl logs <p> [-c <container>] --previous` |
| What happened, in order | `docker events --since 30m --filter container=<c>` | same | `docker events --filter service=<svc>` | `kubectl get events --sort-by=.lastTimestamp` |
| Resource use now | `docker stats --no-stream` | `docker compose stats` | `docker stats` on the node | `kubectl top pod` (metrics-server) |
| Processes | `docker top <c>` | `docker compose top` | on the node | `kubectl exec <p> -- ps` (if the image has `ps`) |
| A shell in a fresh copy | ⚠️ `docker run --rm -it --entrypoint sh <img>` | ⚠️ `docker compose run --rm --entrypoint sh <svc>` | as Docker, on any node | ⚠️ `kubectl run dbg --rm -it --image=<img> --command -- sh` |
| A shell in the running one | ⚠️ `docker exec -it <c> sh` | ⚠️ `docker compose exec <svc> sh` | ⚠️ `docker exec` on the node | ⚠️ `kubectl exec -it <p> -- sh` |
| Tools beside a shell-less one | ⚠️ `docker run --rm -it --network container:<c> --pid container:<c> nicolaka/netshoot` | same, with the container name | same, on the node | ⚠️ `kubectl debug -it <p> --image=busybox --target=<container>` |

---

## The `inspect` templates that answer most questions

None prints environment values. `Config.Env` contains secrets — print names only.

```bash
docker inspect <c> --format 'status={{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}} err={{.State.Error}} started={{.State.StartedAt}} finished={{.State.FinishedAt}} restarts={{.RestartCount}}'
docker inspect <c> --format 'entrypoint={{json .Config.Entrypoint}} cmd={{json .Config.Cmd}} user={{.Config.User}} workdir={{.Config.WorkingDir}}'
docker inspect <c> --format 'mem={{.HostConfig.Memory}} swap={{.HostConfig.MemorySwap}} pids={{.HostConfig.PidsLimit}} ro={{.HostConfig.ReadonlyRootfs}} capdrop={{.HostConfig.CapDrop}}'
docker inspect <c> --format '{{json .State.Health}}'                                   # the probe's own output, per attempt
docker inspect <c> --format '{{json .NetworkSettings.Networks}}'                      # which networks, which aliases
docker inspect <c> --format '{{json .NetworkSettings.Ports}}'                         # what's published, on which address
docker inspect <c> --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}} rw={{.RW}}{{"\n"}}{{end}}'
docker inspect <c> --format '{{range .Config.Env}}{{println .}}{{end}}' | cut -d= -f1   # names only
docker image inspect <img> --format '{{.Os}}/{{.Architecture}} user={{.Config.User}}'
```

---

## Inside the container's view

From a shell in the container, or from a netshoot/busybox sidecar sharing its namespaces:

| Question | Command | Reads |
|---|---|---|
| Who am I, what can I write? | `id; ls -ld <path>; touch <path>/.probe && echo writable` (⚠️ the touch) | uid/gid against ownership |
| Does the name resolve? | `getent hosts <name>`; `cat /etc/resolv.conf` | Docker's embedded DNS is `127.0.0.11` on user-defined networks |
| Is anything listening? | `ss -ltn` (or `netstat -ltn`) | `127.0.0.1:8000` is reachable only from inside; `0.0.0.0:8000` from the network |
| Can I reach it? | `nc -zv <host> <port>`; `curl -v http://<host>:<port>/` | refused (nothing listening) vs timeout (filtered or unroutable) |
| What's the kernel enforcing? | `grep -E 'CapEff\|NoNewPrivs\|Seccomp' /proc/1/status` | capabilities, escalation flag, seccomp mode |
| What's PID 1? | `cat /proc/1/cmdline \| tr '\0' ' '` | `sh -c …` means shell form — signals won't reach the app |
| Memory limit and use (cgroup v2) | `cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.events` | `oom_kill` count in `memory.events` |
| CPU throttling | `cat /sys/fs/cgroup/cpu.stat` | `nr_throttled`, `throttled_usec` |
| A file's real bytes | `od -c <file> \| head -3` | `\r \n` = CRLF |

---

## From the host (when you have it)

| Question | Command | Notes |
|---|---|---|
| What changed in the filesystem? | `docker diff <c>` | `A` added, `C` changed, `D` deleted — write paths, stray logs, core dumps |
| Pull a file out | `docker cp <c>:/path ./out` | works on stopped containers too |
| The whole filesystem, no shell needed | `docker export <c> \| tar -t \| grep <name>` | works on images with no shell or `ls` |
| Enter the namespaces without the image's tools | `nsenter -t $(docker inspect -f '{{.State.Pid}}' <c>) -n ss -ltn` (⚠️ root on the host) | `-n` network, `-m` mount, `-p` pid; uses the **host's** binaries |
| Kernel's view of a kill | `dmesg -T \| grep -iE 'oom\|killed process'` | names the process the OOM killer chose |
| Ports owned on the host | `ss -ltnp` | `docker-proxy` owns published ports (unless userland proxy is off) |
| Disk | `docker system df -v` | images, containers, volumes, build cache |

**Docker Desktop (macOS, Windows):** the engine runs in a VM, so `dmesg`, `nsenter` and
`/var/lib/docker` are inside it, not on your Mac. Use a privileged helper container to reach the VM
only on your own machine, never on a shared host.

---

## Keeping the evidence

- **A forensic snapshot:** ⚠️ `docker commit <c> debug/<c>:$(date +%s)` freezes the container's
  filesystem (not its memory, not its volumes) so you can poke at it after the original is gone.
  It's for investigation only — never ship or tag it as a release, and it may contain shell history
  and secrets written to disk, so keep it local and delete it after.
- **Pause, don't kill,** when a compromise is suspected: `docker pause <c>` freezes the processes and
  keeps memory and state for the incident responders. A kill destroys exactly the evidence they need
  ([container-hardening](../container-hardening/SKILL.md) theory C13).
- **Kubernetes:** `kubectl logs --previous` is the only copy of a crashed container's last output, and
  it lasts only until the next restart replaces it — save it to a file first.

---

## What each tool can't see

| Tool | Blind to |
|---|---|
| `docker logs` | anything the app writes to a file instead of stdout/stderr; logs from before a rotation (with some drivers) |
| `docker inspect` | what happened inside the process; the healthcheck's history beyond the last few attempts |
| `docker exec` | a container that isn't running; an image with no shell |
| `docker stats` | short spikes between samples — an OOM kill can happen between two readings |
| `kubectl describe` | events older than the cluster's event TTL (about an hour by default) |
| A sidecar sharing namespaces | the target's **filesystem** (it has its own) — use `docker cp`/`export` for files |

# Platforms — One Control, Four Spellings

**Contents:** The translation table · Proving it: `docker inspect` templates · Finding candidates: grep signals · Scanners and what they see

> Every control in [`controls.md`](controls.md) as a `docker run` flag, a Compose key, a Kubernetes
> field and a Swarm service option; the `docker inspect` template that proves it took effect; and the
> grep signal that finds a candidate in each file format. **A signal match is a candidate, not a
> finding** — read the workload in context. And **a key in a file is not proof the runtime applied
> it** ([`theory.md`](theory.md) C3): Swarm and older Compose versions drop some keys without a
> warning. Prove with inspect where you can.

---

## The translation table

| Control | `docker run` | Compose (`docker compose`) | Kubernetes (`securityContext` unless noted) | Swarm (`docker stack deploy`) |
|---|---|---|---|---|
| Non-root | `--user 10001:10001` | `user: "10001:10001"` | `runAsUser: 10001`, `runAsGroup: 10001`, `runAsNonRoot: true` | `user:` honoured |
| No escalation | `--security-opt no-new-privileges` | `security_opt: ["no-new-privileges:true"]` | `allowPrivilegeEscalation: false` | `security_opt` **ignored** — set `"no-new-privileges": true` in each node's `daemon.json` |
| Drop capabilities | `--cap-drop ALL --cap-add NET_BIND_SERVICE` | `cap_drop: [ALL]`, `cap_add: [...]` | `capabilities: {drop: ["ALL"], add: [...]}` | `cap_drop`/`cap_add` honoured on Engine 20.10+ |
| Not privileged | (omit `--privileged`) | (omit `privileged`) | `privileged: false` | not available to services |
| Seccomp default | (default) · `--security-opt seccomp=profile.json` | `security_opt: ["seccomp=profile.json"]` | `seccompProfile: {type: RuntimeDefault}` — **must be set** | daemon default only |
| AppArmor / SELinux | `--security-opt apparmor=<p>` / `label=type:<t>` | `security_opt: [...]` | `appArmorProfile: {type: RuntimeDefault}` (1.30+), `seLinuxOptions` | daemon default only |
| Read-only root | `--read-only --tmpfs /tmp:size=64m,noexec,nosuid` | `read_only: true`, `tmpfs: ["/tmp:size=64m,noexec,nosuid"]` | `readOnlyRootFilesystem: true` + an `emptyDir` (`medium: Memory`, `sizeLimit`) | `read_only` honoured; `tmpfs` mounts via `volumes` `type: tmpfs` |
| Memory | `--memory 512m --memory-swap 512m` | `mem_limit: 512m`, `memswap_limit: 512m` (or `deploy.resources.limits.memory`) | `resources.limits.memory` (pod spec) | `deploy.resources.limits.memory` |
| Pids | `--pids-limit 256` | `pids_limit: 256` | kubelet `podPidsLimit` (node setting) | `deploy.resources.limits.pids` (Engine 23.0 and later; `--limit-pids` on `docker service create`) |
| CPU | `--cpus 1.5` | `cpus: 1.5` | `resources.limits.cpu` | `deploy.resources.limits.cpus` |
| Host namespaces | (omit `--pid/--network/--ipc host`) | (omit `pid`, `network_mode`, `ipc`: `host`) | `hostPID/hostNetwork/hostIPC: false` (pod spec) | `network_mode` ignored; host networking via the `host` network |
| User namespaces | daemon `userns-remap` or rootless | same (daemon) | `hostUsers: false` (pod spec; needs kernel and runtime support) | daemon |
| Published port, one interface | `-p 127.0.0.1:5432:5432` | `ports: ["127.0.0.1:5432:5432"]` | `ClusterIP`; no `hostPort`/`NodePort` for internals | routing mesh publishes on **every node**; `mode: host` for one |
| Secrets as files | `--mount type=bind,src=…,dst=/run/secrets/x,ro` | `secrets:` (a **bind mount** outside Swarm) | Secret as a `volume`, not `env` | `secrets:` (encrypted, tmpfs, `uid/gid/mode` honoured) |
| No API token | — | — | `automountServiceAccountToken: false` | — |
| Log rotation | `--log-opt max-size=10m --log-opt max-file=3` | `logging: {driver: local}` or `json-file` with options | node / runtime log rotation | `logging:` honoured |

**Kubernetes in one read-only call:** `kubectl label --dry-run=server --overwrite ns <ns> pod-security.kubernetes.io/enforce=restricted` lists every pod that would violate the **restricted** Pod Security Standard. Restricted requires: non-root, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]` (only `NET_BIND_SERVICE` may be added), `seccompProfile` `RuntimeDefault` or `Localhost`, no privileged, no host namespaces, no `hostPath`, restricted volume types. It does **not** require a read-only root filesystem, resource limits, NetworkPolicies or digest pinning — those stay findings here even when a namespace passes.

---

## Proving it: `docker inspect` templates

Every template is read-only. None prints environment values — `Config.Env` is shown by **name** only.

| Question | Template (`docker inspect <c> --format '…'`) | Good |
|---|---|---|
| User | `{{.Config.User}}` | a non-zero uid |
| Privileged | `{{.HostConfig.Privileged}}` | `false` |
| Capabilities | `add={{.HostConfig.CapAdd}} drop={{.HostConfig.CapDrop}}` | `drop=[ALL]`, minimal add |
| Security options | `{{.HostConfig.SecurityOpt}}` | contains `no-new-privileges` (shown without `:true`); no `unconfined` |
| AppArmor | `{{.AppArmorProfile}}` | `docker-default` or a named profile, not `unconfined`. Empty when the host has no AppArmor (SELinux hosts, Docker Desktop) — then `docker info` says which LSM, if any, is on |
| Namespaces | `pid={{.HostConfig.PidMode}} net={{.HostConfig.NetworkMode}} ipc={{.HostConfig.IpcMode}} userns={{.HostConfig.UsernsMode}}` | none `host` |
| Mounts | `{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}} rw={{.RW}}{{"\n"}}{{end}}` | no socket, no system path, `rw=false` where possible |
| Devices | `{{.HostConfig.Devices}}` | empty or named |
| Read-only root | `{{.HostConfig.ReadonlyRootfs}}` | `true` |
| Limits | `mem={{.HostConfig.Memory}} swap={{.HostConfig.MemorySwap}} pids={{.HostConfig.PidsLimit}} cpus={{.HostConfig.NanoCpus}}` | non-zero; swap = mem. `0` is unlimited, and so is a pids value of `<no value>` or `-1` |
| Published ports | `{{json .NetworkSettings.Ports}}` | `HostIp` is a specific address — not `0.0.0.0`, `::` (the IPv6 twin Docker adds alongside it) or empty |
| Env names (no values) | `{{range .Config.Env}}{{println .}}{{end}}` piped to `cut -d= -f1` | no `*PASSWORD*`, `*SECRET*`, `*TOKEN*`, `*KEY*` |
| Logging | `{{json .HostConfig.LogConfig}}` | rotation options set |

**Inside the container**, only with permission: `grep -E 'CapEff|NoNewPrivs|Seccomp' /proc/1/status` — `NoNewPrivs: 1`, `Seccomp: 2` (filtered); decode `CapEff` on the host with `capsh --decode=<hex>`.

**The daemon:** `docker info --format '{{.SecurityOptions}}'` lists `name=seccomp,profile=builtin`, `name=apparmor` or `name=selinux`, and `name=rootless` / `name=userns` when user namespaces are on.

**Swarm:** `docker service inspect <svc> --format '{{json .Spec.TaskTemplate.ContainerSpec}}'` shows what the service spec actually carries — check it for every key the stack file set, because ignored keys are simply absent.

**Kubernetes:** `kubectl get pod <p> -o jsonpath='{.spec.securityContext}{"\n"}{range .spec.containers[*]}{.name}: {.securityContext}{"\n"}{end}'`.

---

## Finding candidates: grep signals

Run from the repo root. Each is a candidate list for the anti-pattern named in [`controls.md`](controls.md).

| Anti-pattern | Compose / stack files | Kubernetes manifests (render Helm first) | Scripts (`docker run`) |
|---|---|---|---|
| Privileged | `privileged:\s*true` | `privileged:\s*true` | `--privileged` |
| Runtime socket | `docker\.sock\|containerd\.sock\|crio\.sock` | same, under `hostPath` | `-v [^ ]*docker\.sock` |
| Host namespaces | `^\s*(pid\|ipc\|uts\|userns_mode):\s*["']?host\|network_mode:\s*["']?host` | `host(PID\|Network\|IPC):\s*true` | `--(pid\|net\|network\|ipc)[= ]host` |
| Host paths | `^\s*-\s*["']?/(etc\|root\|home\|proc\|sys\|dev\|boot\|var/run\|var/lib/docker\|var/lib/kubelet\|lib/modules)?(/\|:)` | `hostPath:` then `path:` | `-v /[a-z]` |
| Dangerous caps | `cap_add:` then `SYS_ADMIN\|SYS_PTRACE\|SYS_MODULE\|DAC_READ_SEARCH\|NET_ADMIN\|BPF\|SYS_RAWIO\|ALL` | `add:` under `capabilities` | `--cap-add` |
| Seccomp / LSM off | `unconfined\|label[:=]disable` | `type:\s*Unconfined` | `seccomp=unconfined\|apparmor=unconfined` |
| No seccomp (K8s) | — | pod/container specs **without** `seccompProfile` | — |
| Root | services without `user:` whose image has no `USER` | no `runAsNonRoot: true`; `runAsUser:\s*0` | no `--user`/`-u` |
| Escalation | services without `no-new-privileges` | no `allowPrivilegeEscalation:\s*false` | no `no-new-privileges` |
| Writable root | services without `read_only:\s*true` | no `readOnlyRootFilesystem:\s*true` | no `--read-only` |
| No limits | services without `mem_limit`/`deploy.resources.limits` | containers without `resources.limits` | no `--memory` |
| Open ports | `-\s*["']?\d+:\d+` (no address in front) | `type:\s*(NodePort\|LoadBalancer)`, `hostPort:` | `-p \d+:\d+` |
| Committed secret | `(PASSWORD\|SECRET\|TOKEN\|API_KEY\|PRIVATE_KEY)[A-Z_]*\s*[:=]\s*["']?[^$"'\s{]` (a literal, not `${…}`) | `stringData:`/`data:` in a committed `kind: Secret`; literal `value:` under `env` | `-e [A-Z_]*(PASSWORD\|TOKEN\|SECRET)=` |
| Secret as env | `environment:` names matching the above, even as `${VAR}` | `secretKeyRef` under `env`, `envFrom: secretRef` | `-e`/`--env-file` with secrets |
| Mutable image | `image:\s*[^@\s]+(:latest)?\s*$` | same | `docker run [^@]*:latest` |
| Install at start | `command:\|entrypoint:` with `apt-get\|apk add\|pip install\|npm install\|curl .*\| *sh` | same under `command`/`args` | same |
| Token mounted | — | pods without `automountServiceAccountToken:\s*false` | — |

**Absence signals** ("without `user:`") need a per-workload read, not a grep — list the workloads, then check each for the key.

---

## Scanners and what they see

| Tool | Reads | Good for | Blind to |
|---|---|---|---|
| `trivy config .` | Dockerfiles, Compose, Kubernetes, Helm, Terraform | many §1–§4 signals, statically | effective settings, what's internet-facing |
| `trivy image` | an image | CVEs (`--ignore-unfixed`), secrets in layers (`--scanners secret`) | how the image is run |
| `hadolint` | a Dockerfile | image-side hygiene | runtime config |
| `docker-bench-security` | a live host | CIS Docker Benchmark: daemon, host, running containers | anything not on that host |
| `kube-bench` | a node | CIS Kubernetes Benchmark: control plane and kubelet | workload manifests |
| `kubescape`, `polaris`, `checkov` | manifests | Pod Security and NSA/CISA hardening checks | the host |
| `cosign verify`, `docker buildx imagetools inspect` | a registry reference | signatures, SBOM and provenance attestations | whether anything enforces them |

Record which ran. A tool's finding becomes a review finding only once it has its six fields — and a
tool's silence is not a 🟢: they miss the read-only socket mount, the `ufw`-bypassing port, and every
chain.

# Controls — Eight Domains and the Host

> The criteria Review grades against and Harden fixes. Each domain has 🟢 what good looks like, 🔴 the
> anti-patterns (**What / Why / Detect / Fix / Cost / Severity**), and the **Checklist** whose criteria
> are scored proportionally per [`scoring.md`](scoring.md). Every 🔴 names its principle in
> [`theory.md`](theory.md). Find candidates with the signals in [`platforms.md`](platforms.md), then
> read each workload in context — a match is a candidate, not a finding.
>
> In scope for domains 1–7: **workloads** (each Compose service, pod template, Swarm service or
> `docker run` invocation). Domain 8: **images**. The host domain: **hosts and daemons**.

---

## 1. privilege — who the process is, and what it may become

### 🟢 Well done
- Runs as a numeric non-root uid set in the image and enforced by the platform (`runAsNonRoot: true`)
  (C5).
- `no-new-privileges` / `allowPrivilegeEscalation: false` on every workload (C5).
- `cap_drop: [ALL]`, with each `cap_add` named and justified in a comment (C4).
- No setuid/setgid binaries in the image (C5).

### 🔴 Not well done

#### Privileged container
**What:** `privileged: true`, `--privileged`, `securityContext.privileged: true`.
**Why:** All capabilities, every host device, no seccomp, no LSM confinement — a host root shell is one
`mount` away (C6, C7).
**Detect:** grep; `docker inspect -f '{{.HostConfig.Privileged}}'`. ✅.
**Fix:** the specific thing it was for: `devices: [/dev/dri]` for a GPU, one named capability, a sysctl.
`docker:dind` genuinely needs it — move CI builds to rootless BuildKit or a remote builder instead.
**Cost:** finding out what it was actually for; a vendor agent may have to be replaced.
**Severity:** Critical.

#### Running as root
**What:** no `USER` in the image and no `user:` / `runAsUser` override; `runAsUser: 0`; Kubernetes
without `runAsNonRoot: true`.
**Why:** Every other failure is worse as uid 0, which is host uid 0 without user namespaces (C5).
**Detect:** `docker image inspect -f '{{.Config.User}}'` empty; `docker inspect -f '{{.Config.User}}'`;
manifest read. ✅ when observed or when the image is in the repo; ⚠️ for a third-party image you can't
inspect.
**Fix:** a numeric `USER` in the image (to [dockerfile](../dockerfile/SKILL.md)); `user: "10001:10001"`
or `runAsUser`/`runAsNonRoot` in the manifest. Give the uid its write paths.
**Cost:** write-path permission errors on first run; images that drop privileges themselves (some
databases) need their documented uid instead.
**Severity:** High — Critical when it combines with a writable host mount or an added capability.

#### Dangerous capability added
**What:** `cap_add` / `capabilities.add` of `SYS_ADMIN`, `SYS_PTRACE`, `SYS_MODULE`, `DAC_READ_SEARCH`,
`NET_ADMIN`, `BPF`, `SYS_RAWIO`, `ALL`.
**Why:** `SYS_ADMIN` is most of root; `SYS_PTRACE` with a shared PID namespace reads other processes'
memory; `DAC_READ_SEARCH` bypasses file permissions (the "shocker" escape); `SYS_MODULE` loads kernel
code (C4, C6).
**Detect:** grep; `docker inspect -f '{{.HostConfig.CapAdd}}'`; inside: `grep CapEff /proc/1/status`,
decoded on the host with `capsh --decode=<hex>`. ✅.
**Fix:** remove, run, and add back only what an error names. `NET_BIND_SERVICE` is the usual legitimate
one.
**Cost:** one test cycle per capability.
**Severity:** Critical for `SYS_ADMIN`, `SYS_MODULE`, `DAC_READ_SEARCH`, `ALL`; High for the others.

#### Default capabilities kept
**What:** no `cap_drop: [ALL]` / `capabilities.drop: ["ALL"]`.
**Why:** Docker's default set (about 14, including `NET_RAW`, `CHOWN`, `SETUID`, `DAC_OVERRIDE`)
is more than a typical web service uses; `NET_RAW` allows packet spoofing on the container network (C4).
**Detect:** grep for the absence. ✅.
**Fix:** drop all, add back by name.
**Cost:** images that start as root and switch user need `SETUID`/`SETGID`/`CHOWN` back.
**Severity:** Medium.

#### Privilege escalation allowed
**What:** no `security_opt: ["no-new-privileges:true"]`; Kubernetes `allowPrivilegeEscalation` not
`false` (it defaults to true).
**Why:** A setuid binary — `su`, `passwd`, `mount`, an older `ping` — turns a non-root process back
into root (C5).
**Detect:** grep for the absence; `docker inspect -f '{{.HostConfig.SecurityOpt}}'`; inside:
`grep NoNewPrivs /proc/1/status` (1 = set). ✅.
**Fix:** set it. Strip setuid bits in the image too (to dockerfile).
**Cost:** `sudo` inside the container stops working.
**Severity:** High when the image has setuid binaries or runs as root; Medium otherwise.

### Checklist
- [ ] no workload privileged · [ ] every workload non-root (uid ≠ 0, enforced where the platform can) ·
  [ ] no dangerous capability added · [ ] all capabilities dropped, additions named ·
  [ ] escalation blocked

---

## 2. isolation — what of the host the container can see

### 🟢 Well done
- No host namespaces; no host mounts except named data paths, read-only where possible (C6).
- No Docker or containerd socket in any workload; node agents use a scoped API instead (C7).
- User namespaces where the platform offers them: rootless Docker, `userns-remap`, Kubernetes
  `hostUsers: false` (C5).

### 🔴 Not well done

#### Docker socket mounted
**What:** a mount of `/var/run/docker.sock` (or `/run/docker.sock`, `/run/containerd/containerd.sock`,
`/run/crio/crio.sock`, a rootless daemon's `$XDG_RUNTIME_DIR/docker.sock`), **including `:ro`**.
**Why:** The socket is the Docker API. Anyone who can talk to it can start a privileged container that
mounts `/` — host root. `:ro` makes the socket *file* read-only; connecting to it and sending API
requests still works (C6, C7).
**Detect:** grep `docker.sock|containerd.sock|crio.sock`; `docker inspect` mounts. ✅.
**Fix:** what the tool needs, not the socket: a socket proxy that allows only the endpoints it calls
(e.g. read-only `GET /containers` for a monitoring agent), the tool's own API, or the orchestrator's
API with a scoped service account. For CI builds, rootless BuildKit or a remote builder.
**Cost:** a proxy to run and configure; some tools (auto-updaters) exist only to drive the socket and
should be replaced by the deploy pipeline.
**Severity:** Critical — whatever the mount mode.

#### Host namespace shared
**What:** `pid: host` / `hostPID`, `network_mode: host` / `hostNetwork`, `ipc: host` / `hostIPC`,
`uts: host`, `userns_mode: host` on a host that remaps.
**Why:** Host PID sees and signals every host process (with `SYS_PTRACE`, reads their memory); host
network binds every host interface, reaches services bound to the host's `localhost` and bypasses
network policy; host IPC shares memory segments (C6).
**Detect:** grep; `docker inspect` `PidMode`, `NetworkMode`, `IpcMode`. ✅.
**Fix:** remove; a published port instead of the host network; a sidecar or shared process namespace
*within the pod* instead of the host's.
**Cost:** node-level agents (CNI, log shippers, monitoring DaemonSets) legitimately need some of these
— record them as accepted risk with the reason.
**Severity:** Critical for `pid: host`; High for host network and IPC; Critical when combined with
`privileged` or `SYS_PTRACE`.

#### Sensitive host path mounted
**What:** a bind mount / `hostPath` of `/`, `/etc`, `/root`, `/home`, `/var/run`, `/var/lib/docker`,
`/var/lib/kubelet`, `/proc`, `/sys`, `/dev`, `/boot`, `/lib/modules` — writable, or read-only for
paths holding credentials (`/etc/shadow`, `/root/.ssh`, kubelet credentials).
**Why:** A writable `/etc` is a new root user or a cron job on the host; `/var/lib/kubelet` holds other
pods' secrets; `/proc` and `/sys` writes reach the kernel (C6).
**Detect:** grep host-side paths in `volumes:` and `hostPath:`; `docker inspect` mounts with `RW=true`. ✅.
**Fix:** a named volume; the specific file read-only; for log shipping, the container runtime's log
directory read-only and nothing else.
**Cost:** reworking how the tool gets its data.
**Severity:** Critical for writable system paths; High for read-only credential paths; Medium for other
read-only host mounts.

#### Devices passed wholesale
**What:** `devices: ["/dev:/dev"]`, a broad device cgroup rule, or `privileged` for one device.
**Why:** Raw disk devices are the host's filesystem; `/dev/mem` is its memory (C4, C6).
**Detect:** grep `devices:`, `device_cgroup_rules`. ✅.
**Fix:** name the one device (`/dev/dri/renderD128`), read-only where possible.
**Severity:** High.

### Checklist
- [ ] no container runtime socket mounted · [ ] no host PID/network/IPC namespace (or accepted with a
  reason) · [ ] no writable sensitive host path · [ ] devices named individually

---

## 3. kernel — which kernel calls the process may make

### 🟢 Well done
- The runtime's default seccomp profile is in force — on Kubernetes, set explicitly with
  `seccompProfile.type: RuntimeDefault` (C3).
- AppArmor or SELinux enabled on the host and not disabled per workload (C2).
- A custom seccomp profile only where the default blocks something, extending the default by the one
  syscall needed (C4).

### 🔴 Not well done

#### Seccomp or LSM disabled
**What:** `security_opt: ["seccomp=unconfined"]`, `["apparmor=unconfined"]`, `["label=disable"]`;
`seccompProfile.type: Unconfined`; `appArmorProfile.type: Unconfined`.
**Why:** The default seccomp profile blocks dozens of syscalls behind past escapes (`unshare`,
`keyctl`, `mount` variants, `bpf`); removing it widens the kernel surface for every other weakness (C2).
**Detect:** grep; `docker inspect -f '{{.HostConfig.SecurityOpt}} {{.AppArmorProfile}}'`; inside:
`grep Seccomp /proc/1/status` (2 = filtered, 0 = none). ✅.
**Fix:** remove. If something fails, copy the runtime's default profile, add the one syscall the error
names, and load that (`seccomp=./profile.json`, `seccompProfile.type: Localhost`).
**Cost:** one profile file to maintain.
**Severity:** High; Critical with `privileged`-adjacent settings (added `SYS_ADMIN`, host PID).

#### Kubernetes pod with no seccomp profile
**What:** a pod or container with no `seccompProfile` at either level, in a cluster where the kubelet's
`SeccompDefault` is not known to be on.
**Why:** Kubernetes does **not** inherit Docker's default: the pod runs Unconfined. This is the most
common silent gap when a team moves from Docker to Kubernetes (C3).
**Detect:** manifest read for the absence ✅; whether the kubelet default is on is 🔬 without node access.
**Fix:** `securityContext.seccompProfile.type: RuntimeDefault` at pod level.
**Severity:** High for internet-facing workloads; Medium otherwise.

#### Kernel parameters opened
**What:** `sysctls:` that are node-wide or unsafe (`kernel.*` outside the namespaced set, `vm.*`), or
`/proc/sys` writable through a mount.
**Why:** A non-namespaced sysctl changes the host (C6).
**Detect:** grep `sysctls`. ✅.
**Severity:** High for unsafe sysctls; Low for the safe namespaced set (`net.ipv4.ip_unprivileged_port_start`).

### Checklist
- [ ] no workload with seccomp unconfined · [ ] every Kubernetes pod sets `RuntimeDefault` (or a
  Localhost profile) · [ ] no LSM disabled per workload · [ ] no unsafe sysctl

---

## 4. filesystem — what the process can change

### 🟢 Well done
- `read_only: true` / `readOnlyRootFilesystem: true`, with each write path a named volume or a sized
  `tmpfs` (`noexec,nosuid` where the app allows) (C8).
- Mounts of config and secrets read-only (C8).
- No package installs or downloads at container start (C8, C12).

### 🔴 Not well done

#### Writable root filesystem
**What:** no `read_only` / `readOnlyRootFilesystem`.
**Why:** An attacker can drop tools, modify the app's code and persist across process restarts within
the container's life (C8).
**Detect:** grep for the absence; `docker inspect -f '{{.HostConfig.ReadonlyRootfs}}'`. ✅.
**Fix:** set it; find the write paths with `docker diff <c>` after exercising the workload, and give
each a volume or `tmpfs` (`/tmp:size=64m,noexec,nosuid`).
**Cost:** frameworks that write caches in surprising places; one test cycle.
**Severity:** Medium; High on an internet-facing service whose image has a shell and a package manager.

#### Mutable at start
**What:** an entrypoint or command that runs `apt-get`, `apk add`, `pip install`, `npm install`,
`curl … | sh` when the container starts.
**Why:** Code nobody scanned, absent from the SBOM, different on every restart, and impossible on a
read-only root (C8, C12).
**Detect:** grep commands and entrypoint scripts. ✅.
**Fix:** move it into the image build (to dockerfile).
**Severity:** Medium; High when it fetches over plain HTTP or from an unpinned URL.

#### Writable shared volume between trust levels
**What:** the same named volume or bind mount writable by an internet-facing service and read by a
privileged or more trusted one (a web app writing into a directory a root cron job executes from).
**Why:** A write from the exposed service becomes code or config in the trusted one (C9).
**Detect:** cross-reference volume names across workloads. ⚠️.
**Severity:** High when the reader executes what it reads; Medium otherwise.

### Checklist
- [ ] root filesystem read-only, write paths named · [ ] config and secret mounts read-only ·
  [ ] nothing installed at start · [ ] no writable volume shared upward across trust levels

---

## 5. resources — how much damage a runaway can do

### 🟢 Well done
- A memory limit on every workload, with swap equal to it on Docker (`memswap_limit` = `mem_limit`) so
  a leak is killed rather than swapping (C9).
- A pids limit (C9).
- CPU limits or requests where neighbours share the host (C9).
- Log rotation configured (`max-size`/`max-file`, or the `local` driver) so logs can't fill the disk.

### 🔴 Not well done

#### No memory limit
**What:** no `mem_limit` / `deploy.resources.limits.memory` / `resources.limits.memory`.
**Why:** One leak or one hostile request pattern takes the whole host's memory and the kernel's OOM
killer picks a victim — not necessarily this container (C9).
**Detect:** grep for the absence; `docker inspect -f '{{.HostConfig.Memory}}'` (0 = unlimited). ✅.
**Fix:** a limit from observed usage plus headroom (`docker stats` over a normal day).
**Cost:** a wrong limit OOM-kills the service under real load — base it on measurement.
**Severity:** Medium; High on a shared host or node.

#### No pids limit
**What:** no `pids_limit` / `--pids-limit` (Kubernetes: the kubelet's pod pids limit, a node setting).
**Why:** A fork bomb or a thread leak exhausts the host's process table (C9).
**Detect:** `docker inspect -f '{{.HostConfig.PidsLimit}}'` (`<no value>`, `0` or `-1` = unlimited). ✅ on Docker;
🔬 on Kubernetes without node config.
**Severity:** Medium.

#### Unbounded logs
**What:** the default `json-file` driver with no `max-size`, per workload and in `daemon.json`.
**Why:** A chatty or attacked service fills the host disk, which stops every other container (C9).
**Detect:** `docker inspect -f '{{.HostConfig.LogConfig}}'`; grep `logging:`; `daemon.json` is 🔬
without host access.
**Severity:** Low; Medium on a host with several services.

### Checklist
- [ ] memory limit on every workload · [ ] pids limit · [ ] CPU bounded where the host is shared ·
  [ ] logs rotate

---

## 6. network — what reaches the container, and what it reaches

### 🟢 Well done
- Published ports bound to the interface that needs them (`127.0.0.1:` behind a local proxy, a
  private address behind a load balancer); only the edge is published at all (C10).
- Backing services on a network the edge can't reach; on Kubernetes, default-deny ingress and egress
  NetworkPolicies with explicit allows — DNS included — and a CNI that enforces them (C9).
- TLS terminated deliberately at the edge; internal traffic encrypted where the threat model needs it
  (overlay encryption on Swarm, a mesh on Kubernetes).

### 🔴 Not well done

#### Published on every interface
**What:** `ports: ["5432:5432"]`, `-p 5432:5432` — no host address — for anything that isn't the public
edge; `NodePort`/`LoadBalancer` services for internal components.
**Why:** Docker binds `0.0.0.0` and installs iptables rules ahead of the host firewall, so `ufw` /
`firewalld` rules do **not** block a Docker-published port. A database "protected by the firewall" is
on the internet (C10).
**Detect:** grep port mappings without an address; `docker inspect -f '{{json .NetworkSettings.Ports}}'`
(`HostIp` `0.0.0.0`, `::` or empty); on the host, `ss -ltnp`. ✅.
**Fix:** `127.0.0.1:5432:5432`, or no published port at all and reach it over the container network.
If the host firewall is the control, use the `DOCKER-USER` chain, which Docker evaluates first.
**Severity:** Critical for a datastore or admin interface with a weak or default credential; High
otherwise.

#### Flat network
**What:** every service on one network; on Kubernetes, no NetworkPolicy in the namespace, or policies
on a CNI that ignores them (flannel without a policy engine).
**Why:** One compromised service reaches every database and internal API directly (C9).
**Detect:** compose `networks:` read; `kubectl get netpol -n <ns>`; the CNI is 🔬 without cluster access.
**Fix:** a `backend` network (`internal: true` blocks egress too) for datastores; default-deny
policies, then allows — remembering egress to kube-dns on port 53.
**Severity:** Medium; High when an internet-facing service shares a network with a datastore holding
customer data.

#### Host network for convenience
**What:** `network_mode: host` / `hostNetwork: true` on an application workload. (Graded in §2.)

### Checklist
- [ ] no internal service published on all interfaces · [ ] datastores segmented from the edge ·
  [ ] default-deny where the platform supports it, enforced

---

## 7. secrets — where credentials live

### 🟢 Well done
- No credential in the repo, the image or the manifest; delivered at run time as files (Swarm/
  Compose `secrets:`, Kubernetes Secret volumes, a secret-store CSI driver) and read through
  `*_FILE` variables (C11).
- Kubernetes service account tokens not mounted where the workload doesn't call the API
  (`automountServiceAccountToken: false`) (C4).

### 🔴 Not well done

#### Credential committed
**What:** a literal key, password or token in a Compose file, env file, manifest, Helm values file or
`docker run` script in version control.
**Why:** Everyone with repo access — and every fork, clone and CI log — has it, forever (C11).
**Detect:** read; `trivy config`/`trivy fs --scanners secret`; gitleaks. ✅. **Record kind and
location, never the value.**
**Fix:** **rotate first**, then remove and deliver at run time. Removing it from the file does not
remove it from history.
**Severity:** Critical for production credentials; High for anything else live.

#### Secret in the image
**What:** `ENV`/`ARG` secrets, a copied `.env` or key file, a token written by a `RUN` step.
**Why:** Layers are permanent and readable by anyone who can pull the image (C11).
**Detect:** `docker history --no-trunc` (instruction text only); `trivy image --scanners secret` (layer
contents). ✅.
**Fix:** to dockerfile; rotate.
**Severity:** Critical.

#### Secret as an environment variable
**What:** `environment:` / `env:` / `envFrom:` carrying credentials, even interpolated from an
uncommitted `.env` or a Kubernetes Secret.
**Why:** Visible in `docker inspect`, `/proc/<pid>/environ`, crash reports and child processes; can't
rotate without restart (C11).
**Detect:** variable names matching `PASSWORD|SECRET|TOKEN|KEY` in env blocks. ✅.
**Fix:** a file secret and the `*_FILE` convention (Postgres, MySQL and many images support it natively).
**Cost:** the app must read a file; a small change, but a change.
**Severity:** Medium.

#### API token mounted by default
**What:** Kubernetes pods that don't call the API with `automountServiceAccountToken` unset.
**Why:** A compromise gets a cluster credential for free; with a permissive role it's the cluster (C4).
**Detect:** manifest read ✅; what the role allows is `kubectl auth can-i --list --as=system:serviceaccount:<ns>:<sa>` (read-only).
**Severity:** Medium; High when the service account has write permissions.

### Checklist
- [ ] no committed credential · [ ] no secret in any image · [ ] secrets delivered as files ·
  [ ] no API token where none is needed

---

## 8. supply chain — what is running, and whether anyone checked

In scope: each distinct image.

### 🟢 Well done
- Every production reference pinned by digest, with an update bot (Renovate, Dependabot) bumping it (C12).
- Scanned in CI; fixable High/Critical vulnerabilities block or are triaged with an owner (C12).
- An SBOM and provenance attached at build; images signed (cosign, Notation) and the signature —
  or at least the digest — enforced at deploy (admission policy, `--with-registry-auth` + digest) (C12).
- Bases from a trusted, maintained source; third-party images from verified publishers (C12).

### 🔴 Not well done

#### Mutable reference
**What:** `:latest`, no tag, or a tag without a digest in a production manifest.
**Why:** What runs tomorrow isn't what was tested today, and a compromised registry tag runs
everywhere on the next pull (C12).
**Detect:** grep `image:` lines. ✅.
**Fix:** `@sha256:` digest plus an update bot.
**Severity:** High for `latest`/untagged in production; Medium for tag-only.

#### Fixable vulnerabilities shipped
**What:** fixable High/Critical CVEs in the running image.
**Why:** Known, patchable entry points (C12).
**Detect:** `trivy image --severity HIGH,CRITICAL --ignore-unfixed`. ✅ when run; 🔬 when no scanner is
available. Scanners disagree; count, don't panic.
**Fix:** rebuild on a patched base (to dockerfile).
**Severity:** High when internet-facing; Medium otherwise.

#### Unverified at deploy
**What:** no SBOM, no signature, or signatures nothing verifies.
**Detect:** `docker buildx imagetools inspect <ref>` for attestations; `cosign verify` (read-only);
admission policy content is 🔬 without cluster access.
**Severity:** Low for the SBOM alone; Medium when images come from outside the organisation unverified.

### Checklist
- [ ] every production image pinned by digest · [ ] scanned, fixable High/Critical triaged ·
  [ ] SBOM and provenance attached · [ ] signature or digest enforced at deploy

---

## host — the daemon and the node (🔬 without host access)

Evaluated only when the user gives host or cluster-node access, or supplies `docker info`,
`daemon.json`, `docker-bench-security` or `kube-bench` output. Otherwise list each as 🔬 and drop the
domain from the score.

| Control | Detect | Severity if missing |
|---|---|---|
| Daemon API not on plain TCP (`-H tcp://0.0.0.0:2375`); remote access only on 2376 with `--tlsverify` and client certs, or over SSH | `ss -ltnp \| grep -E ':2375\|:2376'`; `daemon.json` `hosts` | Critical |
| `docker` group contains only people who should be host root | `getent group docker` | High |
| User namespaces: rootless Docker or `userns-remap` | `docker info -f '{{.SecurityOptions}}'` shows `rootless` or `userns` | Medium |
| AppArmor or SELinux enabled | `docker info -f '{{.SecurityOptions}}'` | High |
| `live-restore`, log rotation defaults, `no-new-privileges` default in `daemon.json` | read `daemon.json` | Low |
| Engine, kernel and runtime (`runc`, `containerd`) patched | `docker version`, `uname -r` | High when a known escape CVE applies |
| A minimal container OS (Bottlerocket, Flatcar, Talos) or a host dedicated to containers | inventory | Low |
| Runtime detection (Falco, Tetragon) with rules scoped per image, alerting off-host | deployment read | Medium for internet-facing estates |
| Swarm: manager autolock, join tokens rotated, odd manager count | `docker info`, `docker node ls` | Medium |

# Theory — The Principles Every Hardening Finding Cites (C1–C13)

**Contents:** Part A: What a container is · Part B: Privilege · Part C: Surface and blast radius · Part D: Secrets and supply chain

> Every finding in a review names one of these. Each principle states **what it says**, **why it
> matters** for a running container, and **what violating it looks like** in a manifest. Sources:
>
> | Short name | Source |
> |---|---|
> | **CS** | Liz Rice, *Container Security*, 2nd ed. (O'Reilly, 2025) |
> | **DIA** | Jeff Nickoloff & Stephen Kuenzli, *Docker in Action*, 2nd ed. (Manning, 2019) |
> | **DUR** | Sean Kane & Karl Matthias, *Docker: Up & Running*, 2nd ed. (O'Reilly, 2018) |
> | **DDD** | Nigel Poulton, *Docker Deep Dive* (2018) |
> | **CS101** | Practical DevSecOps, *Container Security 101* (ebook) |
> | **PSS** | Kubernetes Pod Security Standards (baseline / restricted), current docs |
> | **CIS** | CIS Docker Benchmark and CIS Kubernetes Benchmark |
>
> Chapters, not pages: the editions used have no stable page numbering. CS (2025) is current on
> BuildKit, Sigstore, SLSA and Kubernetes 1.33. DIA, DUR and DDD predate Pod Security Admission,
> rootless Docker as a default option and keyless signing; where they are cited, the principle comes
> from the book and the mechanism is named as current practice.

---

## Part A — What a container is

### C1 — The kernel is shared; a container is a process
**Says:** A container is an ordinary Linux process whose view is narrowed by namespaces, whose
consumption is bounded by cgroups, and whose kernel access is cut down by a capability set, a
seccomp filter and an LSM profile (AppArmor or SELinux). There is no hypervisor between it and the
host kernel (CS ch. 1–4, 8; DIA ch. 6; DUR ch. 11). So the threat model starts from the host: what
can a compromised process in this container reach on the machine, and on the other containers?
Actors to name: external attackers, compromised dependencies, insiders with deploy rights, other
tenants on the node (CS ch. 1).
**Violation:** treating "it's in a container" as a security boundary on its own; a review that lists
settings without saying what a compromise could reach; running untrusted or multi-tenant workloads
on a shared kernel with no sandbox (gVisor, Kata, a VM per tenant) where the threat model needs one.

### C2 — Isolation is several independent fences
**Says:** Namespaces, cgroups, capabilities, seccomp, the LSM and user namespaces are separate
mechanisms; an escape needs one of them to fail *and* the others to let it through. Each is worth
keeping even when another is present (CS ch. 8, 11; defense in depth, CS ch. 1).
**Violation:** dropping seccomp "because we run as non-root"; `--privileged` "because AppArmor is
on"; disabling the LSM to fix one permission error.

### C3 — Effective settings, not written ones
**Says:** What a runtime applies is the written config plus its defaults, and the defaults differ by
runtime: Docker applies a default seccomp profile and AppArmor/SELinux profile; Kubernetes runs a pod
**Unconfined** unless `seccompProfile` is set or the kubelet's `SeccompDefault` is on (CS ch. 8;
PSS). Docker runs as the image's `USER`, which is root when unset. Swarm and older Compose versions
ignore some keys silently.
**Violation:** reviewing only the lines that exist; assuming Docker's seccomp default carries over to
Kubernetes; reporting a setting as fixed because the YAML says so.

---

## Part B — Privilege

### C4 — Least privilege
**Says:** A process gets only the privileges its job needs, and nothing by default it could lose
without breaking (CS ch. 1, 11; CIS). For containers: drop all capabilities and add back by name;
no privilege escalation; the narrowest mounts, devices and network reach that work.
**Violation:** default capability set kept for a web service; `cap_add` of broad capabilities
(`SYS_ADMIN`, `NET_ADMIN`, `SYS_PTRACE`, `DAC_READ_SEARCH`, `SYS_MODULE`, `BPF`) without a reason;
`allowPrivilegeEscalation` left at its default (true).

### C5 — Root is the multiplier
**Says:** Without user-namespace remapping, uid 0 in a container is uid 0 on the host; every fence
failing (a kernel bug, a sensitive mount, an added capability) is worse when the process is root
(CS ch. 11; DIA ch. 6; DUR ch. 11). Non-root by number, `no-new-privileges`, and no setuid binaries
are three separate controls against the same multiplier. User namespaces (rootless Docker,
`userns-remap`, Kubernetes `hostUsers: false`) remove it at the host level.
**Violation:** no `USER` in the image and no `user:` / `runAsUser` in the manifest; `runAsUser: 0`;
`runAsNonRoot` absent; setuid binaries present with escalation allowed.

### C6 — Root on the host is reachable through interfaces, not just exploits
**Says:** Some configuration hands the host to the container outright: `--privileged` (all
capabilities, all devices, no seccomp, no LSM confinement); the Docker socket (an API that can start a
privileged container mounting `/` — `:ro` restricts the file, not the API); host PID, network or IPC
namespaces; writable mounts of `/`, `/etc`, `/var/run`, `/proc`, `/sys`, `/dev`, `/var/lib/docker`,
`/var/lib/kubelet` (CS ch. 11; DIA ch. 6; DDD ch. 15; CIS).
**Violation:** any of the above on a workload that isn't a node-level agent with a stated need —
and even then, recorded as accepted risk.

### C7 — Host interfaces are root
**Says:** The corollary that sets severity: a workload with a host-root interface is a full host
compromise one application bug away. These are **Critical** regardless of what else is hardened
(CS ch. 11; DDD ch. 15). Membership of the `docker` group is the same thing for a human (CS ch. 11).
**Violation:** a monitoring, CI or "auto-update" container with the socket; `privileged` to reach one
device; a CI runner on a production cluster with the socket.

---

## Part C — Surface and blast radius

### C8 — Smallest attack surface
**Says:** What isn't in the image or reachable at run time can't be used: no shell or package manager
in production images, no unused services, minimal base images, a read-only root filesystem with named
write paths (CS ch. 7, 12; CS101 ch. 2; DIA ch. 8).
**Violation:** writable root filesystem on an internet-facing service; full OS base images in
production; `apt-get`/`pip install` at container start; a shell started in a production container
treated as routine.

### C9 — Limit the blast radius
**Says:** A compromised or misbehaving container should be bounded: memory and pids limits (a fork
bomb or leak takes down only itself), CPU limits where neighbours matter, network segmentation and
default-deny so a compromise can't reach every peer, per-workload identities (CS ch. 3, 12; DIA ch. 6;
DUR ch. 5).
**Violation:** no memory or pids limit; every service on one flat network with the database;
no NetworkPolicy, or one the CNI doesn't enforce; the default service account token mounted into
every pod.

### C10 — Expose only what must be reached
**Says:** A published port is an entry point; it should listen on the interface that needs it and no
other. Docker publishes on `0.0.0.0` by default and inserts its own iptables rules, which bypass
host firewalls such as `ufw` and `firewalld` (DIA ch. 5; DUR ch. 11).
**Violation:** a database or admin UI published on all interfaces; "the firewall blocks it" for a
Docker-published port; `network_mode: host` / `hostNetwork: true` for a service that only needs a port.

---

## Part D — Secrets and supply chain

### C11 — Secrets are files, delivered at run time
**Says:** Credentials never enter the image (layers are permanent and readable by anyone who can
pull), and are delivered at run time as files on a tmpfs rather than environment variables, which
leak through `docker inspect`, `/proc/<pid>/environ`, crash dumps, child processes and logs, and
can't be rotated without a restart (CS ch. 14; DIA ch. 12–13; DDD ch. 14).
**Violation:** a literal credential in a manifest or env file in the repo; `ENV`/`ARG` secrets in a
Dockerfile; Kubernetes Secrets injected as env; secrets in a ConfigMap.

### C12 — Know what you ship, and ship only what you verified
**Says:** An image is pinned by digest, built from a known base, scanned for known vulnerabilities,
described by an SBOM, and signed — and the platform verifies the signature (or the digest) before
it runs it. A digest without an update bot freezes vulnerabilities; a signature nothing verifies
protects nothing (CS ch. 6–7, 10; CS101 ch. 2).
**Violation:** `:latest` or tag-only references in production manifests; no scan, or a scan whose
fixable Criticals ship anyway; no SBOM; signing without verification at admission; Docker Content
Trust as the plan (retired — use Sigstore cosign or Notation).

### C13 — Observe at run time, and act deliberately
**Says:** Preventive controls fail; runtime detection (Falco, Tetragon) and audit logs catch what
gets through — an unexpected shell, a write to `/etc`, an outbound connection that wasn't in the
profile. Choose per rule whether to alert or to prevent, because a "prevent" that kills a pod under
a replica controller becomes a crash loop (CS ch. 15; CS101 ch. 5). Quarantine (pause, snapshot)
before killing, to keep the evidence.
**Violation:** no runtime detection or audit trail on internet-facing workloads; generic rules that
fire in every container and get muted; responses that destroy forensic state.

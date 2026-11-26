---
description: Route an audit to the right skill, a database (dbaudit), network (netaudit) or security (appsec, hardening, threatmodel) audit.
argument-hint: "[what to audit]"
disable-model-invocation: true
---

Audit this: $ARGUMENTS

Work out which kind of audit it is from the arguments and from what the repository holds, then hand
off to that skill and follow its instructions:

- **Database** (DDL, schema, migrations, a data model): `dbaudit`.
- **Network** (topology, device configs, addressing, firewall rules): `netaudit`.
- **Security**, by what is under review:
  - application code, a repository or an API: `appsec`;
  - Linux hosts or a cloud estate: `hardening`;
  - an architecture, a design document or a threat model: `threatmodel`.

If the evidence fits none of these, or more than one, ask one question that names the candidates
before starting. Run one audit at a time; when several apply, say which one comes next.

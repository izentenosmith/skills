#!/usr/bin/env bash
# Build the release-notes fixture's git repository: Beacon, an uptime-monitoring
# SaaS, with tags v2.2.0, v2.3.0 and v2.4.0 and three unreleased commits after
# the last tag. Squash-merge history: one commit per PR, the PR body as the body.
# Idempotent: removes and rebuilds repo/ each time.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf repo && mkdir repo && cd repo

git init -q -b main
git config user.email "fixture@example.invalid"
git config user.name "Fixture"
git config commit.gpgsign false
git config tag.gpgsign false

commit() { # commit <iso-date> <author> <subject> [body]
  GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" \
  GIT_AUTHOR_NAME="$2" GIT_COMMITTER_NAME="$2" \
  GIT_AUTHOR_EMAIL="${2// /.}@example.invalid" \
  GIT_COMMITTER_EMAIL="${2// /.}@example.invalid" \
  git commit -q --allow-empty -m "$3" ${4:+-m "$4"}
}

tag() { # tag <iso-date> <name> <message> — annotated, so the tag carries its own date
  GIT_COMMITTER_DATE="$1" GIT_COMMITTER_NAME="Release Bot" \
  GIT_COMMITTER_EMAIL="release-bot@example.invalid" \
  git tag -a "$2" -m "$3"
}

version() { # version <x.y.z> — the one line package.json carries
  sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$1\"/" package.json && rm package.json.bak
}

mkdir -p src/api src/auth src/export src/incidents src/mail src/maintenance src/notify src/sla \
         src/db/migrations web/src/i18n test .github/workflows

# ================================================================ before 2.3.0
cat > package.json <<'EOF'
{
  "name": "beacon",
  "version": "2.2.0",
  "private": true,
  "scripts": {
    "build": "tsc -p .",
    "test": "vitest run",
    "lint": "eslint ."
  },
  "dependencies": {
    "fastify": "4.28.1",
    "pg": "8.12.0",
    "saml-verify": "3.1.2"
  },
  "devDependencies": {
    "eslint": "9.1.0",
    "typescript": "5.5.4",
    "vitest": "1.6.0"
  }
}
EOF
cat > README.md <<'EOF'
# Beacon

Uptime monitoring for teams: HTTP, TCP and cron monitors, alerting, and a public
status page per workspace. Web app at app.beaconhq.example, REST API at
api.beaconhq.example.

- Documentation: https://docs.beaconhq.example
- API reference: https://docs.beaconhq.example/api
- Support: https://beaconhq.example/support
- Community forum: https://community.beaconhq.example

## Development

    pnpm install
    pnpm test

Releases are cut by tagging `vX.Y.Z` on main. The tag is what ships.
EOF
cat > CONTRIBUTING.md <<'EOF'
# Contributing

Open a PR against main. Squash-merge only; the PR title becomes the commit
subject, so prefix it with feat/fix/perf/chore and the PLAT ticket.
EOF
cat > CHANGELOG.md <<'EOF'
# Changelog

## 2.3.0

- feat: status page custom domains [PLAT-388] (#231)
- fix: handle ECONNRESET in HttpProbe (#233)
- perf: memoize WorkspaceSettings lookup (#236)
- chore(deps): bump fastify to 4.28.1 (#238)

## 2.2.0

- feat(api): add /v2/hooks with signed payloads and retries [PLAT-371] (#221)
- feat: cron monitors (#219)
- fix: incident auto-resolve fired twice (#224)
EOF
cat > src/api/pagination.ts <<'EOF'
export const DEFAULT_PAGE_SIZE = 500;
export const MAX_PAGE_SIZE = 500;

export function pageSize(limit?: number): number {
  if (limit === undefined) return DEFAULT_PAGE_SIZE;
  return Math.min(Math.max(1, limit), MAX_PAGE_SIZE);
}
EOF
cat > src/api/webhooks.ts <<'EOF'
import type { FastifyInstance } from "fastify";

// /v1/webhooks: unsigned, fire-and-forget. /v2/hooks (src/api/hooks.ts) supersedes it.
export function registerV1Webhooks(app: FastifyInstance) {
  app.post("/v1/webhooks", async (req, reply) => {
    return reply.send(await createWebhook(req.body));
  });
}

declare function createWebhook(body: unknown): Promise<unknown>;
EOF
cat > src/auth/saml.ts <<'EOF'
import { verifyAssertion } from "saml-verify";

// Every SAML single sign-on login goes through here.
export async function samlLogin(xml: string, idpCert: string) {
  const assertion = await verifyAssertion(xml, { cert: idpCert });
  return { email: assertion.nameId, workspaceId: assertion.attributes.workspace };
}
EOF
cat > src/export/csv.ts <<'EOF'
import type { Pool } from "pg";

export async function exportChecks(db: Pool, workspaceId: string, days: number): Promise<string> {
  const { rows } = await db.query(
    "SELECT monitor_id, checked_at, status, latency_ms FROM check_results " +
      "WHERE workspace_id = $1 AND checked_at > now() - ($2 || ' days')::interval ORDER BY checked_at",
    [workspaceId, days],
  );
  return rows.map((r) => `${r.monitor_id},${r.checked_at.toISOString()},${r.status},${r.latency_ms}`).join("\n");
}
EOF
cat > src/incidents/timeline.ts <<'EOF'
import type { Pool } from "pg";

export class IncidentTimelineQuery {
  constructor(private db: Pool) {}

  async run(workspaceId: string, incidentId: string) {
    const { rows } = await this.db.query(
      "SELECT kind, body, created_at FROM incident_events " +
        "WHERE workspace_id = $1 AND incident_id = $2 ORDER BY created_at",
      [workspaceId, incidentId],
    );
    return rows;
  }
}
EOF
cat > src/mail/DigestMailer.ts <<'EOF'
import { formatInTimeZone } from "./tz";

export class DigestMailer {
  render(workspace: { name: string; timezone: string }, uptime: number): string {
    const week = formatInTimeZone(new Date(), workspace.timezone, "d MMM yyyy");
    return `Weekly uptime report for ${workspace.name}, week of ${week}: ${uptime.toFixed(2)}%`;
  }
}
EOF
cat > src/sla/SlaCalculator.ts <<'EOF'
export class SlaCalculator {
  // Uptime percentage for one calendar month.
  monthly(downtimes: { start: Date; end: Date }[], monthStart: Date, monthEnd: Date): number {
    const total = monthEnd.getTime() - monthStart.getTime();
    const down = downtimes
      .filter((d) => d.start >= monthStart && d.start < monthEnd)
      .reduce((s, d) => s + (d.end.getTime() - d.start.getTime()), 0);
    return 100 * (1 - down / total);
  }
}
EOF
cat > src/notify/NotificationService.ts <<'EOF'
export class NotificationService {
  async incidentUpdate(incident: { id: string; channel: string }, text: string) {
    await this.postToSlack(incident.channel, text);
  }

  private async postToSlack(channel: string, text: string) {
    await fetch("https://slack.com/api/chat.postMessage", {
      method: "POST",
      body: JSON.stringify({ channel, text }),
    });
  }
}
EOF
cat > src/flags.ts <<'EOF'
export const flags: Record<string, boolean> = {
  custom_domains: true,
};
EOF
cat > web/src/i18n/en.json <<'EOF'
{
  "monitor.settings": "Settings",
  "statuspage.down": "Down",
  "statuspage.operational": "Operational"
}
EOF
cat > .github/workflows/ci.yml <<'EOF'
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: pnpm install
      - run: pnpm lint && pnpm test
EOF
cat > test/sla.test.ts <<'EOF'
import { expect, test } from "vitest";
import { SlaCalculator } from "../src/sla/SlaCalculator";

test("no downtime is 100%", () => {
  const m = new SlaCalculator().monthly([], new Date("2026-09-01"), new Date("2026-09-30"));
  expect(m).toBe(100);
});
EOF
git add -A
commit "2026-07-15T10:00:00+00:00" "Maya Okafor" "chore(release): 2.2.0"
tag "2026-07-15T10:10:00+00:00" v2.2.0 "Beacon 2.2.0"

commit "2026-08-11T14:22:00+00:00" "Jonas Berg" "feat: status page custom domains [PLAT-388] (#231)"
commit "2026-08-19T09:41:00+00:00" "Lucía Ferrer" "fix: handle ECONNRESET in HttpProbe (#233)"
commit "2026-08-26T16:05:00+00:00" "Jonas Berg" "perf: memoize WorkspaceSettings lookup (#236)"
commit "2026-08-28T08:12:00+00:00" "dependabot[bot]" "chore(deps): bump fastify to 4.28.1 (#238)"
version 2.3.0
git add -A
commit "2026-09-02T11:30:00+00:00" "Maya Okafor" "chore(release): 2.3.0"
tag "2026-09-02T11:40:00+00:00" v2.3.0 "Beacon 2.3.0"

# ============================================================ v2.3.0..v2.4.0
# (#251) a user-facing feature behind an internal class name, flag and ticket
cat > src/maintenance/MaintenanceWindowScheduler.ts <<'EOF'
import { flags } from "../flags";

export type MaintenanceWindow = { monitorId: string; start: Date; end: Date; weekly: boolean };

export class MaintenanceWindowScheduler {
  constructor(private windows: MaintenanceWindow[]) {}

  // Alerts are muted and the status page shows "Under maintenance" while a window is open.
  isUnderMaintenance(monitorId: string, at: Date): boolean {
    if (!flags.maint_windows_v2) return false;
    return this.windows.some((w) => w.monitorId === monitorId && this.covers(w, at));
  }

  private covers(w: MaintenanceWindow, at: Date): boolean {
    if (!w.weekly) return at >= w.start && at < w.end;
    const week = 7 * 24 * 3600 * 1000;
    const offset = (at.getTime() - w.start.getTime()) % week;
    return offset >= 0 && offset < w.end.getTime() - w.start.getTime();
  }
}
EOF
cat > src/flags.ts <<'EOF'
export const flags: Record<string, boolean> = {
  custom_domains: true,
  maint_windows_v2: true, // on for every workspace from 2.4.0; kill switch only
};
EOF
cat > web/src/i18n/en.json <<'EOF'
{
  "maintenance.cta": "Schedule maintenance",
  "maintenance.recurring": "Repeat every week",
  "maintenance.title": "Maintenance windows",
  "monitor.settings": "Settings",
  "statuspage.down": "Down",
  "statuspage.maintenance": "Under maintenance",
  "statuspage.operational": "Operational"
}
EOF
git add -A
commit "2026-09-08T13:15:00+00:00" "Jonas Berg" \
  "feat: MaintenanceWindowScheduler + maint_windows_v2 flag [PLAT-412] (#251)" \
  "Adds MaintenanceWindowScheduler. A user can schedule a maintenance window on a
monitor, one-off or repeating weekly, from the monitor's Settings tab
(\"Schedule maintenance\"). While the window is open, alerts for that monitor are
muted and the public status page shows it as \"Under maintenance\" instead of Down.

maint_windows_v2 defaults to true for every workspace as of this release; the
flag is only kept as a kill switch and goes away in 2.5.

Branch: feat/plat-412-maint-windows"

# (#252) shipped inside the range ... and reverted by #265 below
cat > src/notify/NotificationService.ts <<'EOF'
export class NotificationService {
  async incidentUpdate(incident: { id: string; channel: string; threadTs?: string }, text: string) {
    await this.postToSlack(incident.channel, text, incident.threadTs);
  }

  private async postToSlack(channel: string, text: string, threadTs?: string) {
    await fetch("https://slack.com/api/chat.postMessage", {
      method: "POST",
      body: JSON.stringify({ channel, text, thread_ts: threadTs }),
    });
  }
}
EOF
git add -A
commit "2026-09-11T10:48:00+00:00" "Lucía Ferrer" \
  "feat(slack): post incident updates as thread replies [PLAT-418] (#252)" \
  "Instead of a new Slack message for every incident update, updates are posted as
replies in the incident's original message thread, so a channel with several open
incidents stays readable. Closes #300.

Branch: feat/plat-418-slack-threads"
SLACK_SHA=$(git rev-parse HEAD)

# (#253) an improvement nobody measured
mkdir -p src/db/migrations
cat > src/db/migrations/0042_incident_events_timeline_idx.sql <<'EOF'
CREATE INDEX CONCURRENTLY IF NOT EXISTS incident_events_timeline_idx
  ON incident_events (workspace_id, incident_id, created_at);
EOF
git add -A
commit "2026-09-15T15:30:00+00:00" "Sam Whitfield" \
  "perf: covering index for IncidentTimelineQuery (#253)" \
  "IncidentTimelineQuery was doing a sequential scan of incident_events on large
workspaces. Adds an index on (workspace_id, incident_id, created_at).

Feels a lot snappier locally on the seeded dataset. I haven't benchmarked it
against production-sized data. Fixes #309."

# (#254) a fix written as its cause; the issue states the symptom
cat > src/mail/DigestMailer.ts <<'EOF'
import { formatInTimeZone } from "./tz";

export class DigestMailer {
  render(workspace: { name: string; timezone: string | null }, uptime: number): string {
    const week = formatInTimeZone(new Date(), workspace.timezone ?? "UTC", "d MMM yyyy");
    return `Weekly uptime report for ${workspace.name}, week of ${week}: ${uptime.toFixed(2)}%`;
  }
}
EOF
git add -A
commit "2026-09-18T11:02:00+00:00" "Lucía Ferrer" \
  "fix: guard null tz in DigestMailer.render (#254)" \
  "DigestMailer.render threw a TypeError when workspace.timezone was null, which it
is for workspaces provisioned through SCIM. The digest job swallowed the error and
moved on. Falls back to UTC now.

Fixes #318"

# (#255) a deprecation with a date and a replacement
cat > src/api/webhooks.ts <<'EOF'
import type { FastifyInstance } from "fastify";

// /v1/webhooks: unsigned, fire-and-forget. /v2/hooks (src/api/hooks.ts) supersedes it.
// Deprecated in 2.4.0; removed on 2027-03-31.
export function registerV1Webhooks(app: FastifyInstance) {
  app.post("/v1/webhooks", async (req, reply) => {
    reply.header("Deprecation", "true");
    reply.header("Sunset", "Wed, 31 Mar 2027 00:00:00 GMT");
    reply.header("Link", '<https://docs.beaconhq.example/api/webhooks-v2-migration>; rel="deprecation"');
    return reply.send(await createWebhook(req.body));
  });
}

declare function createWebhook(body: unknown): Promise<unknown>;
EOF
git add -A
commit "2026-09-22T09:20:00+00:00" "Maya Okafor" \
  "feat(api): deprecate /v1/webhooks, add Sunset header [PLAT-430] (#255)" \
  "/v1/webhooks now answers with Deprecation: true and
Sunset: Wed, 31 Mar 2027 00:00:00 GMT. It is removed on 2027-03-31.

The replacement is /v2/hooks (shipped in 2.2.0): same events, plus signed payloads
and retries. Migration guide:
https://docs.beaconhq.example/api/webhooks-v2-migration"

# (#256) an improvement with a measured number in the PR body
cat > src/export/csv.ts <<'EOF'
import type { Pool } from "pg";
import Cursor from "pg-cursor";
import type { Writable } from "node:stream";

export async function exportChecks(db: Pool, workspaceId: string, days: number, out: Writable) {
  const client = await db.connect();
  try {
    const cursor = client.query(new Cursor(
      "SELECT monitor_id, checked_at, status, latency_ms FROM check_results " +
        "WHERE workspace_id = $1 AND checked_at > now() - ($2 || ' days')::interval ORDER BY checked_at",
      [workspaceId, days],
    ));
    for (let rows = await cursor.read(5000); rows.length; rows = await cursor.read(5000)) {
      out.write(rows.map((r) => `${r.monitor_id},${r.checked_at.toISOString()},${r.status},${r.latency_ms}\n`).join(""));
    }
  } finally {
    client.release();
  }
}
EOF
git add -A
commit "2026-09-25T14:44:00+00:00" "Sam Whitfield" \
  "perf(export): stream CSV export rows instead of buffering (#256)" \
  "The check-results CSV export built the whole file in memory before sending the
first byte. It now streams rows from a server-side cursor.

Measured on staging against the largest workspace snapshot (1.2M check results,
90-day export), p50 over 10 runs: 48 s before, 11 s after. Peak memory of the
export worker: 1.9 GB before, 140 MB after."

# (#257) a fix written as its cause; the issue states the symptom
cat > src/sla/SlaCalculator.ts <<'EOF'
export class SlaCalculator {
  // Uptime percentage for one calendar month.
  monthly(downtimes: { start: Date; end: Date }[], monthStart: Date, monthEnd: Date): number {
    const total = monthEnd.getTime() - monthStart.getTime();
    const down = downtimes
      .filter((d) => d.start >= monthStart && d.start <= monthEnd)
      .reduce((s, d) => s + (d.end.getTime() - d.start.getTime()), 0);
    return 100 * (1 - down / total);
  }
}
EOF
git add -A
commit "2026-09-29T17:10:00+00:00" "Jonas Berg" \
  "fix: off-by-one in SlaCalculator month window (#257)" \
  "SlaCalculator.monthly compared the end bound with < instead of <=, so a downtime
starting on the last day of the month was outside the window. Closes #322."

# (#259) one line, filed as a chore, and breaking for every API client that lists
sed -i.bak 's/DEFAULT_PAGE_SIZE = 500/DEFAULT_PAGE_SIZE = 50/' src/api/pagination.ts && rm src/api/pagination.ts.bak
git add -A
commit "2026-10-01T10:35:00+00:00" "Maya Okafor" \
  "chore(api): lower DEFAULT_PAGE_SIZE to 50 (#259)" \
  "500 was causing statement timeouts on the list endpoints for big workspaces.

GET /v1/monitors, /v1/checks and /v1/incidents now return 50 items per page when
the caller passes no limit, instead of 500. An integration that read a whole list
in one request without passing limit now gets only the first 50; it has to follow
next_cursor, or pass limit (still capped at 500)."

# (#260) a plain bump
sed -i.bak 's/"eslint": "9.1.0"/"eslint": "9.2.0"/' package.json && rm package.json.bak
git add -A
commit "2026-10-02T06:01:00+00:00" "dependabot[bot]" \
  "chore(deps): bump eslint from 9.1.0 to 9.2.0 (#260)" \
  "Bumps eslint from 9.1.0 to 9.2.0."

# (#261) a bump that patches a CVE users are exposed to
sed -i.bak 's/"saml-verify": "3.1.2"/"saml-verify": "3.1.4"/' package.json && rm package.json.bak
git add -A
commit "2026-10-02T06:03:00+00:00" "dependabot[bot]" \
  "chore(deps): bump saml-verify from 3.1.2 to 3.1.4 (#261)" \
  "Bumps saml-verify from 3.1.2 to 3.1.4.

3.1.4 fixes CVE-2026-41207: signature validation could be bypassed with a crafted
SAML response, letting an attacker sign in as another member of a workspace that
uses SAML single sign-on.

(Maya) We call saml-verify on every SAML SSO login (src/auth/saml.ts), so this
applies to us. Nothing in the auth logs suggests it was exploited."

# (#262-#264) CI, tests, refactor
cat > .github/workflows/ci.yml <<'EOF'
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/cache@v4
        with: { path: ~/.pnpm-store, key: "pnpm-${{ hashFiles('pnpm-lock.yaml') }}" }
      - run: pnpm install
      - run: pnpm lint && pnpm test
EOF
git add -A
commit "2026-10-03T12:00:00+00:00" "Sam Whitfield" "ci: cache pnpm store between jobs (#262)"

cat >> test/sla.test.ts <<'EOF'

test("downtime on the last day of the month counts", () => {
  const m = new SlaCalculator().monthly(
    [{ start: new Date("2026-09-30T10:00:00Z"), end: new Date("2026-09-30T10:40:00Z") }],
    new Date("2026-09-01T00:00:00Z"), new Date("2026-09-30T23:59:59Z"),
  );
  expect(m).toBeLessThan(100);
});
EOF
git add -A
commit "2026-10-05T15:25:00+00:00" "Jonas Berg" "test: cover SlaCalculator month boundaries (#263)"

cat > src/notify/AlertRouter.ts <<'EOF'
// Decides which channels an alert goes to. Extracted from NotificationService.
export class AlertRouter {
  route(alert: { severity: string }, channels: string[]): string[] {
    return alert.severity === "critical" ? channels : channels.slice(0, 1);
  }
}
EOF
git add -A
commit "2026-10-07T11:50:00+00:00" "Lucía Ferrer" \
  "refactor: extract AlertRouter from NotificationService [PLAT-433] (#264)" \
  "No behaviour change."

# (#265) the Slack thread replies come back out
cat > src/notify/NotificationService.ts <<'EOF'
export class NotificationService {
  async incidentUpdate(incident: { id: string; channel: string }, text: string) {
    await this.postToSlack(incident.channel, text);
  }

  private async postToSlack(channel: string, text: string) {
    await fetch("https://slack.com/api/chat.postMessage", {
      method: "POST",
      body: JSON.stringify({ channel, text }),
    });
  }
}
EOF
git add -A
commit "2026-10-09T16:40:00+00:00" "Lucía Ferrer" \
  "Revert \"feat(slack): post incident updates as thread replies [PLAT-418] (#252)\" (#265)" \
  "This reverts commit ${SLACK_SHA}.

Slack rate-limited thread replies on large workspaces during the canary. Pulling it
from 2.4 until updates are batched; #300 stays open."

# (#266-#268) docs, lint, a dev-only bump
sed -i.bak 's/prefix it with/prefix it with one of/' CONTRIBUTING.md && rm CONTRIBUTING.md.bak
git add -A
commit "2026-10-10T09:05:00+00:00" "Sam Whitfield" "docs: fix typo in CONTRIBUTING (#266)"

printf '\n' >> src/notify/AlertRouter.ts
git add -A
commit "2026-10-12T10:30:00+00:00" "Jonas Berg" "style: apply eslint 9.2 autofixes (#267)"

sed -i.bak 's/"vitest": "1.6.0"/"vitest": "2.0.5"/' package.json && rm package.json.bak
git add -A
commit "2026-10-13T06:02:00+00:00" "dependabot[bot]" \
  "chore(deps-dev): bump vitest from 1.6.0 to 2.0.5 (#268)" \
  "Bumps vitest from 1.6.0 to 2.0.5."

version 2.4.0
git add -A
commit "2026-10-14T15:20:00+00:00" "Maya Okafor" "chore(release): 2.4.0"
tag "2026-10-14T15:30:00+00:00" v2.4.0 "Beacon 2.4.0"

# ================================================== after v2.4.0 — unreleased
cat > src/notify/sms.ts <<'EOF'
// SMS alerts through Twilio. Not released yet.
export async function sendSms(to: string, body: string) {
  await fetch("https://api.twilio.com/2010-04-01/Accounts/ACxxxx/Messages.json", {
    method: "POST",
    body: new URLSearchParams({ To: to, Body: body }),
  });
}
EOF
git add -A
commit "2026-10-16T13:00:00+00:00" "Lucía Ferrer" \
  "feat: SMS alerts via Twilio [PLAT-440] (#270)" \
  "Adds SMS as an alert channel. Closes #327."

cat > web/src/i18n/en.json <<'EOF'
{
  "maintenance.cta": "Schedule maintenance",
  "maintenance.recurring": "Repeat every week",
  "maintenance.title": "Maintenance windows",
  "monitor.settings": "Settings",
  "statuspage.down": "Down",
  "statuspage.favicon": "/favicon.ico",
  "statuspage.maintenance": "Under maintenance",
  "statuspage.operational": "Operational"
}
EOF
git add -A
commit "2026-10-19T09:45:00+00:00" "Jonas Berg" "fix: status page favicon 404 on custom domains (#271)"

version 2.5.0-dev
git add -A
commit "2026-10-21T08:30:00+00:00" "Maya Okafor" "chore: start 2.5.0-dev"

echo "built $(git rev-list --count HEAD) commits in $(pwd);" \
     "v2.3.0..v2.4.0 = $(git rev-list --count v2.3.0..v2.4.0) commits," \
     "$(git rev-list --count v2.4.0..HEAD) after the tag"

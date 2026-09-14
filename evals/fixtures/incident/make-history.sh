#!/usr/bin/env bash
# Build the incident fixture's git repository with backdated commits.
# Idempotent: removes and rebuilds repo/ each time.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf repo && mkdir repo && cd repo

git init -q -b main
git config user.email "fixture@example.invalid"
git config user.name "Fixture"
git config commit.gpgsign false

commit() { # commit <iso-date> <author> <subject> [body]
  GIT_AUTHOR_DATE="$1" GIT_COMMITTER_DATE="$1" \
  GIT_AUTHOR_NAME="$2" GIT_COMMITTER_NAME="$2" \
  GIT_AUTHOR_EMAIL="${2// /.}@example.invalid" \
  GIT_COMMITTER_EMAIL="${2// /.}@example.invalid" \
  git commit -q --allow-empty -m "$3" ${4:+-m "$4"}
}

mkdir -p ledger tests config

# ---------------------------------------------------------------- 2026-07-14
cat > ledger/__init__.py <<'EOF'
__version__ = "2.1.0"
EOF
cat > ledger/statements.py <<'EOF'
"""Account statement queries."""


def recent_entries(conn, account_id, limit=500):
    return conn.execute(
        "SELECT id, posted_at, amount_cents, memo "
        "FROM entries WHERE account_id = %s "
        "ORDER BY posted_at DESC LIMIT %s",
        (account_id, limit),
    ).fetchall()
EOF
cat > config/database.yml <<'EOF'
production:
  host: db-primary.internal
  pool: 20
  # statement_timeout: intentionally unset — some month-end reconciliation
  # queries legitimately run for several minutes.
EOF
git add -A
commit "2026-07-14T09:12:00+00:00" "Priya Raman" "add account statement queries" \
  "Paginated at 500 entries. The LIMIT is what keeps this bounded on the large
reconciliation accounts."

# ---------------------------------------------------------------- 2026-07-22
cat > ledger/export.py <<'EOF'
"""CSV export of account entries."""

from ledger.statements import recent_entries


def export_account(conn, account_id):
    rows = recent_entries(conn, account_id)
    return "\n".join(
        f"{r[0]},{r[1].isoformat()},{r[2]},{r[3]}" for r in rows
    )
EOF
git add -A
commit "2026-07-22T11:40:00+00:00" "Tomas Lind" "add CSV export for account entries"

# ------------------------------------------------- THE TRIGGER — 2026-07-26
# Nine days before the outage. Reachable only by widening the date range.
cat > ledger/statements.py <<'EOF'
"""Account statement queries."""


def recent_entries(conn, account_id, limit=None):
    sql = (
        "SELECT id, posted_at, amount_cents, memo "
        "FROM entries WHERE account_id = %s ORDER BY posted_at DESC"
    )
    params = [account_id]
    if limit is not None:
        sql += " LIMIT %s"
        params.append(limit)
    return conn.execute(sql, params).fetchall()
EOF
git add -A
commit "2026-07-26T16:31:00+00:00" "Priya Raman" "make the statement limit optional" \
  "Finance need full-history exports for the annual audit and 500 rows is not
enough. Default is now unbounded; callers that want a page pass limit=.

Reviewed-by: Tomas Lind"

cat > ledger/export.py <<'EOF'
"""CSV export of account entries."""

from ledger.statements import recent_entries


def export_account(conn, account_id):
    # Audit export: no limit, we want the whole history.
    rows = recent_entries(conn, account_id)
    return "\n".join(
        f"{r[0]},{r[1].isoformat()},{r[2]},{r[3]}" for r in rows
    )
EOF
git add -A
commit "2026-07-26T16:44:00+00:00" "Priya Raman" "export the full history for audit"

# ---------------------------------------------------------------- quiet days
cat > tests/test_export.py <<'EOF'
def test_export_formats_rows(fake_conn):
    assert "," in export_account(fake_conn, 1)
EOF
git add -A
commit "2026-07-29T10:02:00+00:00" "Tomas Lind" "add a smoke test for the exporter"
commit "2026-07-31T14:20:00+00:00" "Tomas Lind" "bump pytest to 8.2.1"
commit "2026-08-01T09:55:00+00:00" "Ana Beltrán" "tidy the statements docstring"

# ------------------------------------------------ THE INCIDENT — 2026-08-04
cat > ledger/statements.py <<'EOF'
"""Account statement queries."""


def recent_entries(conn, account_id, limit=500):
    return conn.execute(
        "SELECT id, posted_at, amount_cents, memo "
        "FROM entries WHERE account_id = %s "
        "ORDER BY posted_at DESC LIMIT %s",
        (account_id, limit),
    ).fetchall()
EOF
cat > ledger/export.py <<'EOF'
"""CSV export of account entries."""

from ledger.statements import recent_entries


def export_account(conn, account_id):
    rows = recent_entries(conn, account_id)
    return "\n".join(
        f"{r[0]},{r[1].isoformat()},{r[2]},{r[3]}" for r in rows
    )
EOF
git add -A
commit "2026-08-04T15:02:00+00:00" "Ana Beltrán" "Revert \"make the statement limit optional\"" \
  "Reverts the unbounded query. Connection pool saturated on db-primary;
statement API returning 503 for all accounts.

This restores the 500-row cap. The audit export is broken again by this —
finance have been told."

cat > config/database.yml <<'EOF'
production:
  host: db-primary.internal
  pool: 20
  statement_timeout: 30s
EOF
git add -A
commit "2026-08-04T18:47:00+00:00" "Ana Beltrán" "set a statement_timeout on production" \
  "No query should be able to hold a pool connection indefinitely, whatever
the caller asks for."

cat > ledger/export.py <<'EOF'
"""CSV export of account entries."""

from ledger.statements import recent_entries

AUDIT_PAGE = 5000


def export_account(conn, account_id, page_size=AUDIT_PAGE):
    """Export in bounded pages rather than one unbounded query."""
    out, offset = [], 0
    while True:
        rows = recent_entries(conn, account_id, limit=page_size, offset=offset)
        if not rows:
            break
        out += [f"{r[0]},{r[1].isoformat()},{r[2]},{r[3]}" for r in rows]
        offset += page_size
    return "\n".join(out)
EOF
git add -A
commit "2026-08-05T11:18:00+00:00" "Priya Raman" "paginate the audit export" \
  "Gives finance the full history back without an unbounded query."

commit "2026-08-06T09:30:00+00:00" "Tomas Lind" "add a regression test for export paging"

echo "built $(git rev-list --count HEAD) commits in $(pwd)"

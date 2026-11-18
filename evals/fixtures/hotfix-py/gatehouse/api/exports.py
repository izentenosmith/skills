from gatehouse.api.reports import REPORTS
from gatehouse.api.responses import forbidden, ok
from gatehouse.auth.scopes import Forbidden, require_scope


def run_export(token, report_id):
    """POST /exports — the report as CSV lines."""
    try:
        require_scope(token, "exports:run")
    except Forbidden as e:
        return forbidden(e.scope)
    rows = REPORTS.get(report_id, [])
    header = ",".join(rows[0]) if rows else ""
    lines = [",".join(str(v) for v in r.values()) for r in rows]
    return ok({"id": report_id, "csv": [header, *lines] if rows else []})

from gatehouse.api.responses import forbidden, ok
from gatehouse.auth.scopes import Forbidden, require_scope

REPORTS = {
    "weekly-signups": [{"week": "2026-W44", "signups": 312}, {"week": "2026-W45", "signups": 298}],
    "churn": [],
}


def get_report(token, report_id):
    """GET /reports/<id>"""
    try:
        require_scope(token, "reports:read")
    except Forbidden as e:
        return forbidden(e.scope)
    return ok({"id": report_id, "rows": list(REPORTS.get(report_id, []))})

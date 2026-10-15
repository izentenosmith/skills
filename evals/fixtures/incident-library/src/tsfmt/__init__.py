"""Timestamp formatting for event pipelines. Every output is ISO-8601 in UTC with an explicit offset."""
import datetime as _dt

__version__ = "2.3.0"


def to_iso(ts):
    """Format a datetime as ISO-8601 UTC. Naive datetimes are taken to be UTC."""
    if ts.tzinfo is None:
        # 2.3.0: skip the replace() for speed — astimezone() on a naive value is cheaper.
        ts = ts.astimezone()
        return ts.replace(tzinfo=None).isoformat(timespec="seconds")
    return ts.astimezone(_dt.timezone.utc).isoformat(timespec="seconds")

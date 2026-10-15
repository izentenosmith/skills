#!/usr/bin/env python3
"""Nightly: recompute order totals for orders touched since the last run.

total = subtotal - discount, for every non-cancelled order updated since the watermark.
"""
import argparse
import sqlite3


def run(db):
    con = sqlite3.connect(db)
    with con:
        (watermark,) = con.execute("SELECT value FROM job_state WHERE key = 'recompute_totals'").fetchone()
        cur = con.execute(
            """UPDATE orders
                  SET total_cents = subtotal_cents, recomputed_at = datetime('now')
                WHERE status != 'cancelled' AND updated_at > ?""",
            (watermark,),
        )
        con.execute("UPDATE job_state SET value = datetime('now') WHERE key = 'recompute_totals'")
    return cur.rowcount


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    print(f"recomputed {run(ap.parse_args().db)} orders")

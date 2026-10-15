#!/usr/bin/env python3
"""Morning: create an invoice for every order whose total changed since its last invoice."""
import argparse
import sqlite3


def run(db):
    con = sqlite3.connect(db)
    with con:
        cur = con.execute(
            """INSERT INTO invoices (order_id, amount_cents, issued_at)
               SELECT id, total_cents, datetime('now') FROM orders
                WHERE status != 'cancelled'
                  AND id NOT IN (SELECT order_id FROM invoices WHERE amount_cents = orders.total_cents)"""
        )
    return cur.rowcount


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    print(f"issued {run(ap.parse_args().db)} invoices")

import os

import psycopg


def connect():
    """Open a connection to the orders database."""
    return psycopg.connect(os.environ["DATABASE_URL"])


def fetch_order(order_id):
    with connect() as conn:
        row = conn.execute(
            "SELECT id, customer, total_cents, status FROM orders WHERE id = %s",
            (order_id,),
        ).fetchone()
    return row

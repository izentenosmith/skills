"""Brightcart order service — data access (psycopg 3)."""


def list_recent_orders(conn, since, page):
    orders = conn.execute(
        "SELECT order_id, customer_id, total, created_at FROM sales_order "
        "WHERE status = 'open' AND created_at >= %s "
        "ORDER BY created_at DESC LIMIT 50 OFFSET %s",
        (since, page * 50),
    ).fetchall()
    result = []
    for order in orders:
        lines = conn.execute(
            "SELECT product_id, qty, unit_price FROM order_line WHERE order_id = %s",
            (order.order_id,),
        ).fetchall()
        result.append((order, lines))
    return result


def find_customer_by_email(conn, email):
    return conn.execute(
        "SELECT customer_id, name, email FROM customer WHERE lower(email) = lower(%s)",
        (email,),
    ).fetchone()


def marketing_export(conn):
    return conn.execute(
        "SELECT customer_id, email FROM customer "
        "WHERE customer_id NOT IN (SELECT customer_id FROM blocked_customer)"
    ).fetchall()


def reserve_stock(conn, product_id, qty):
    with conn.transaction():
        row = conn.execute(
            "SELECT stock FROM product WHERE product_id = %s", (product_id,)
        ).fetchone()
        if row.stock < qty:
            raise ValueError("out of stock")
        conn.execute(
            "UPDATE product SET stock = %s WHERE product_id = %s",
            (row.stock - qty, product_id),
        )


def search_products(conn, term, sort):
    # sort comes straight from the ?sort= query parameter
    return conn.execute(
        f"SELECT product_id, sku, name, unit_price FROM product WHERE name ILIKE %s ORDER BY {sort}",
        ("%" + term + "%",),
    ).fetchall()


def monthly_report(conn, month_start, month_end):
    return conn.execute(
        "SELECT p.sku, sum(l.qty) AS units, sum(l.qty * l.unit_price) AS revenue "
        "FROM sales_order o JOIN order_line l ON l.order_id = o.order_id "
        "JOIN product p ON p.product_id = l.product_id "
        "WHERE o.created_at >= %s AND o.created_at < %s GROUP BY p.sku",
        (month_start, month_end),
    ).fetchall()

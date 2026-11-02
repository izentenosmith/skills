"""Payment provider webhook."""


def payment_succeeded(pg, payload):
    pg.execute(
        "INSERT INTO payment (order_id, amount, provider) VALUES (%s, %s, %s)",
        (payload["order_id"], payload["amount"], "paystream"),
    )
    pg.execute("UPDATE ticket_order SET status = 'paid' WHERE order_id = %s", (payload["order_id"],))
    pg.commit()
    return 200

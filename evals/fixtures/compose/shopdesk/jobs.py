from shopdesk import db


def fulfil(order_id):
    order = db.fetch_order(order_id)
    if order is None:
        raise ValueError(f"no such order: {order_id}")
    return {"order": order_id, "state": "fulfilled"}


def invoice(order_id):
    order = db.fetch_order(order_id)
    return {"order": order_id, "total_cents": order[2] if order else 0}

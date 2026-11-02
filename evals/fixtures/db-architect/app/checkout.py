"""Seat hold and purchase path."""


def hold_seat(pg, redis, search, event_id, seat_no, customer_id):
    key = f"seat:{event_id}:{seat_no}"
    if redis.get(key) != b"free":
        raise SeatTaken(seat_no)
    pg.execute(
        "INSERT INTO seat_hold (event_id, seat_no, customer_id, expires_at) "
        "VALUES (%s, %s, %s, now() + interval '10 minutes')",
        (event_id, seat_no, customer_id),
    )
    pg.commit()
    redis.set(key, "held")


def complete_order(pg, redis, search, order):
    pg.execute("INSERT INTO ticket_order (order_id, customer_id, total) VALUES (%s, %s, %s)",
               (order.id, order.customer_id, order.total))
    pg.commit()
    for seat in order.seats:
        redis.set(f"seat:{order.event_id}:{seat}", "sold")
    search.index(index="orders", id=order.id, document=order.as_dict())


class SeatTaken(Exception):
    pass

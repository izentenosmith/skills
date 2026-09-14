import os

import redis
from rq import Queue

# Order fulfilment is queued, not synchronous: a job enqueued here is picked up
# by `rq worker` and must survive until a worker takes it.
_conn = redis.from_url(os.environ["REDIS_URL"])

fulfilment = Queue("fulfilment", connection=_conn)
invoices = Queue("invoices", connection=_conn)


def enqueue_fulfilment(order_id):
    return fulfilment.enqueue("shopdesk.jobs.fulfil", order_id)


def enqueue_invoice(order_id):
    return invoices.enqueue("shopdesk.jobs.invoice", order_id)

import os

from flask import Flask, jsonify, request

from shopdesk import db, queue, search

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev")

PORT = int(os.environ.get("PORT", "8000"))


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/orders/<int:order_id>")
def get_order(order_id):
    row = db.fetch_order(order_id)
    if row is None:
        return jsonify(error="not found"), 404
    return jsonify(id=row[0], customer=row[1], total_cents=row[2], status=row[3])


@app.post("/orders/<int:order_id>/fulfil")
def fulfil_order(order_id):
    job = queue.enqueue_fulfilment(order_id)
    queue.enqueue_invoice(order_id)
    return jsonify(job=job.id), 202


@app.get("/products")
def products():
    return jsonify(results=search.find_products(request.args.get("q", "")))

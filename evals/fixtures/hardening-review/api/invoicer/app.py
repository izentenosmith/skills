import os

import stripe
from flask import Flask, jsonify

app = Flask(__name__)
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]


@app.get("/healthz")
def healthz():
    return jsonify(ok=True)

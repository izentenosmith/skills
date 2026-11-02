import os

import redis
from flask import Flask, jsonify

app = Flask(__name__)
cache = redis.Redis.from_url(os.environ["REDIS_URL"])


@app.get("/cart")
def cart():
    return jsonify(items=int(cache.get("cart:demo") or 0))

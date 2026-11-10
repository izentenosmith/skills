"""Queues the hourly cart cleanup. Runs forever; stopped and recreated on every deploy."""
import os
import time

import redis

queue = redis.Redis.from_url(os.environ["REDIS_URL"])
print("scheduler started", flush=True)
last = None
while True:
    hour = time.strftime("%Y-%m-%dT%H", time.gmtime())
    if hour != last:
        queue.rpush("cleanup", "carts")
        last = hour
    time.sleep(30)

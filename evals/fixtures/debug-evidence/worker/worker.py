"""Thumbnail worker: pulls jobs from Redis, classifies and resizes images."""
import os
import time

import redis
import torchvision

print("loading model resnet50", flush=True)
model = torchvision.models.resnet50(weights="DEFAULT")  # ~100 MB of weights, ~400 MB resident once loaded
model.eval()
print("model loaded", flush=True)

queue = redis.Redis.from_url(os.environ["REDIS_URL"])
while True:
    job = queue.blpop("thumbnails", timeout=5)
    time.sleep(0.1)

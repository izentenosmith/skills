import json
import os
import zlib

FLAGS_FILE = os.environ.get("FLAGS_FILE", "config/flags.json")


def enabled(name, user_id):
    """Re-read on every call, so a flag flip takes effect without a deploy."""
    with open(FLAGS_FILE) as fh:
        flag = json.load(fh).get(name, {})
    if not flag.get("enabled"):
        return False
    return zlib.crc32(str(user_id).encode()) % 100 < flag.get("rollout_percent", 100)

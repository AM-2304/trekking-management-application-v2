"""Small Redis cache helper.

Only trek listings and the admin counts are cached. Slot counts and bookings never
are, because a stale slot count would be a correctness bug. If Redis is down these
behave like a miss, so the app keeps working.

    redis-cli KEYS 'tma:*'
"""

import hashlib
import json

import redis
from flask import current_app

_client = None


def get_client():
    """One shared, lazily-created Redis client."""
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            current_app.config["REDIS_URL"], decode_responses=True
        )
    return _client


def make_key(prefix, **parts):
    """e.g. make_key("treks", q="base", page=1) -> "tma:treks:3f9a1c2b"."""
    if not parts:
        return f"tma:{prefix}"
    raw = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"tma:{prefix}:{digest}"


def get_json(key):
    """Return the cached value, or None on a miss or any Redis problem."""
    try:
        raw = get_client().get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def set_json(key, value, ttl):
    """Cache a value for `ttl` seconds. Silently does nothing if Redis is down."""
    try:
        get_client().set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        pass


def invalidate():
    """Drop cached trek listings and dashboard counts. Call after any trek or
    booking write."""
    try:
        client = get_client()
        keys = list(client.scan_iter("tma:treks*")) + list(client.scan_iter("tma:admin*"))
        if keys:
            client.delete(*keys)
    except Exception:
        pass

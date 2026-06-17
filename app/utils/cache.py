"""Simple in-memory cache for frequent queries."""

import time
import threading
from functools import wraps

_lock = threading.Lock()
_cache = {}

def get_cache(key: str) -> object | None:
    val = _cache.get(key)
    if val is None:
        return None
    if val["expires_at"] < time.time():
        del _cache[key]
        return None
    return val["data"]

def set_cache(key: str, data: object, ttl_seconds: int = 30):
    with _lock:
        _cache[key] = {
            "data": data,
            "expires_at": time.time() + ttl_seconds,
        }

def invalidate_cache(prefix: str = ""):
    with _lock:
        if prefix:
            keys = [k for k in _cache if k.startswith(prefix)]
            for k in keys:
                del _cache[k]
        else:
            _cache.clear()

def cached(ttl: int = 30):
    """Decorator: cache function result in memory."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function name + args
            key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            result = get_cache(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            set_cache(key, result, ttl)
            return result
        return wrapper
    return decorator

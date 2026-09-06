"""
Tiny in-memory attempt tracker.

Kept intentionally simple (no Redis/DB) per the project's "no unnecessary
dependencies" rule. This means attempt counts reset if the remediation pod
restarts -- an acceptable trade-off for a demo project, and called out
explicitly in explaination.md.
"""
import time
import threading

_lock = threading.Lock()
_attempts = {}  # key: "namespace/kind/name" -> {"count": int, "first_seen": ts}


def _key(namespace, kind, name):
    return f"{namespace}/{kind}/{name}"


def record_attempt(namespace, kind, name, window_seconds):
    key = _key(namespace, kind, name)
    now = time.time()
    with _lock:
        entry = _attempts.get(key)
        if entry is None or (now - entry["first_seen"]) > window_seconds:
            entry = {"count": 0, "first_seen": now}
        entry["count"] += 1
        _attempts[key] = entry
        return entry["count"]


def get_attempts(namespace, kind, name, window_seconds):
    key = _key(namespace, kind, name)
    now = time.time()
    with _lock:
        entry = _attempts.get(key)
        if entry is None or (now - entry["first_seen"]) > window_seconds:
            return 0
        return entry["count"]


def reset_attempts(namespace, kind, name):
    key = _key(namespace, kind, name)
    with _lock:
        _attempts.pop(key, None)

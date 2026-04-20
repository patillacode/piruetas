import time
from collections import defaultdict
from threading import Lock

_lock = Lock()
_attempts: dict[str, list[float]] = defaultdict(list)

MAX_ATTEMPTS = 10
WINDOW = 900  # 15 minutes


def is_rate_limited(ip: str) -> bool:
    now = time.time()
    with _lock:
        _attempts[ip] = [t for t in _attempts[ip] if now - t < WINDOW]
        return len(_attempts[ip]) >= MAX_ATTEMPTS


def record_failed_attempt(ip: str) -> None:
    with _lock:
        _attempts[ip].append(time.time())


def clear_attempts(ip: str) -> None:
    with _lock:
        _attempts.pop(ip, None)

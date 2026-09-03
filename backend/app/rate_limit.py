import os
import time
from collections import defaultdict, deque
from threading import Lock


LOGIN_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "5"))
WINDOW_SECONDS = int(os.getenv("LOGIN_RATE_WINDOW_SECONDS", "60"))
_attempts = defaultdict(deque)
_lock = Lock()


def allow_login(ip: str) -> bool:
    now = time.monotonic()
    with _lock:
        attempts = _attempts[ip]
        while attempts and attempts[0] <= now - WINDOW_SECONDS:
            attempts.popleft()
        return len(attempts) < LOGIN_LIMIT


def record_failed_login(ip: str):
    with _lock:
        _attempts[ip].append(time.monotonic())


def clear_login_attempts(ip: str):
    with _lock:
        _attempts.pop(ip, None)

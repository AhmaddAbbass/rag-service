from contextlib import contextmanager
from threading import Lock

_lock = Lock()
_locks: dict[str, Lock] = {}


@contextmanager
def attempt_lock(attempt_id: str):
    with _lock:
        if attempt_id not in _locks:
            _locks[attempt_id] = Lock()
        lock = _locks[attempt_id]
    lock.acquire()
    try:
        yield
    finally:
        lock.release()

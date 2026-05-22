"""Rate limit + circuit breaker for error capture.

Both use the Django cache so they work across processes on a single host.
Fail-open: any cache error must NOT prevent capture.
"""
import logging

from django.core.cache import cache

logger = logging.getLogger(__name__)

RATE_LIMIT_WINDOW = 60       # seconds
RATE_LIMIT_MAX = 10          # captures per fingerprint per window

CB_FAIL_THRESHOLD = 20       # failures in window that trip the breaker
CB_FAIL_WINDOW = 60          # rolling window for failures
CB_COOLDOWN = 300            # how long the breaker stays open

_RL_PREFIX = "ai_mon:rl:"
_CB_FAILS = "ai_mon:cb:fails"
_CB_OPEN = "ai_mon:cb:open"


def check_rate_limit(fingerprint: str) -> bool:
    """Return True if capture is allowed, False if this fingerprint is over its budget."""
    key = f"{_RL_PREFIX}{fingerprint}"
    try:
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, RATE_LIMIT_WINDOW)
            count = 1
        return count <= RATE_LIMIT_MAX
    except Exception:
        return True


def circuit_is_open() -> bool:
    try:
        return bool(cache.get(_CB_OPEN))
    except Exception:
        return False


def record_capture_failure():
    try:
        try:
            count = cache.incr(_CB_FAILS)
        except ValueError:
            cache.set(_CB_FAILS, 1, CB_FAIL_WINDOW)
            count = 1
        if count >= CB_FAIL_THRESHOLD:
            cache.set(_CB_OPEN, True, CB_COOLDOWN)
            logger.error("ai_monitoring circuit breaker OPEN for %ds", CB_COOLDOWN)
    except Exception:
        pass


def reset_capture_failures():
    try:
        cache.delete(_CB_FAILS)
    except Exception:
        pass

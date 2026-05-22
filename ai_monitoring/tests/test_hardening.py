"""Rate limit, circuit breaker, and async dispatch hardening."""
import importlib.util
import sys
import unittest
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from ai_monitoring import ratelimit
from ai_monitoring.models import ErrorLog, ErrorOccurrence
from ai_monitoring.services import capture_exception

# django-q is an optional dependency — the async-dispatch tests are skipped when
# it is not installed (the package falls back to synchronous alerts in that case).
_HAS_DJANGO_Q = importlib.util.find_spec("django_q") is not None


def _raise_value_error():
    try:
        raise ValueError("rate-limit-boom")
    except ValueError:
        return capture_exception(sys.exc_info())


class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_captures_under_limit_all_recorded(self):
        for _ in range(ratelimit.RATE_LIMIT_MAX):
            _raise_value_error()
        self.assertEqual(ErrorOccurrence.objects.count(), ratelimit.RATE_LIMIT_MAX)

    def test_captures_over_limit_dropped(self):
        for _ in range(ratelimit.RATE_LIMIT_MAX + 5):
            _raise_value_error()
        # Only RATE_LIMIT_MAX recorded; excess dropped
        self.assertEqual(ErrorOccurrence.objects.count(), ratelimit.RATE_LIMIT_MAX)
        group = ErrorLog.objects.get()
        self.assertEqual(group.occurrence_count, ratelimit.RATE_LIMIT_MAX)


class CircuitBreakerTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_open_breaker_skips_capture(self):
        cache.set(ratelimit._CB_OPEN, True, 60)
        group, created, should_notify = _raise_value_error()
        self.assertIsNone(group)
        self.assertEqual(ErrorLog.objects.count(), 0)

    def test_db_failure_trips_breaker(self):
        # Lower threshold so rate limit on same fingerprint doesn't block us.
        with patch.object(ratelimit, "CB_FAIL_THRESHOLD", 3), \
             patch("ai_monitoring.services._write_capture", side_effect=RuntimeError("db down")):
            for _ in range(3):
                try:
                    _raise_value_error()
                except RuntimeError:
                    pass
        self.assertTrue(ratelimit.circuit_is_open())

    def test_success_resets_failure_counter(self):
        cache.set(ratelimit._CB_FAILS, 5, 60)
        _raise_value_error()
        self.assertIsNone(cache.get(ratelimit._CB_FAILS))


@unittest.skipUnless(_HAS_DJANGO_Q, "django-q (optional dependency) is not installed")
class AsyncDispatchTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_dispatch_uses_async_task(self):
        from ai_monitoring.middleware import _dispatch_alert

        group = ErrorLog.objects.create(fingerprint="z", exception_type="X")
        with patch("django_q.tasks.async_task") as mock_async:
            _dispatch_alert(group)
            mock_async.assert_called_once_with(
                "ai_monitoring.tasks.send_alert_task", group.pk
            )

    def test_dispatch_falls_back_to_sync_on_async_failure(self):
        from ai_monitoring.middleware import _dispatch_alert

        group = ErrorLog.objects.create(fingerprint="z2", exception_type="X")
        with patch("django_q.tasks.async_task", side_effect=Exception("q down")), \
             patch("ai_monitoring.notifications.send_alert") as mock_sync:
            _dispatch_alert(group)
            mock_sync.assert_called_once_with(group)


class SendAlertTaskTests(TestCase):
    def test_task_loads_group_and_sends(self):
        from ai_monitoring.tasks import send_alert_task

        group = ErrorLog.objects.create(fingerprint="t", exception_type="X")
        with patch("ai_monitoring.notifications.send_alert") as mock_send:
            send_alert_task(group.pk)
            mock_send.assert_called_once()
            self.assertEqual(mock_send.call_args[0][0].pk, group.pk)

    def test_task_missing_group_is_noop(self):
        from ai_monitoring.tasks import send_alert_task

        with patch("ai_monitoring.notifications.send_alert") as mock_send:
            send_alert_task(99999)
            mock_send.assert_not_called()

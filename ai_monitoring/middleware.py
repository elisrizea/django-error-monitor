"""Middleware that captures unhandled exceptions into ErrorLog."""
import logging
import sys

from django.http import Http404

from ai_monitoring.services import capture_exception

logger = logging.getLogger(__name__)


class ErrorCaptureMiddleware:
    """Capture unhandled exceptions via process_exception hook.

    Returning None lets Django's normal error handling continue (500 page).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, Http404):
            return None
        try:
            group, created, should_notify = capture_exception(
                sys.exc_info(), request=request
            )
            if should_notify and group is not None:
                _dispatch_alert(group)
        except Exception:
            # Never let monitoring break the request
            logger.exception("ai_monitoring: failed to capture exception")
        return None


def _dispatch_alert(group):
    """Queue send_alert via django-q; fall back to sync if unavailable."""
    try:
        from django_q.tasks import async_task
        async_task("ai_monitoring.tasks.send_alert_task", group.pk)
        return
    except Exception:
        logger.warning("ai_monitoring: async dispatch failed, sending alert synchronously")
    try:
        from ai_monitoring.notifications import send_alert
        send_alert(group)
    except Exception:
        logger.exception("ai_monitoring: synchronous alert fallback failed")

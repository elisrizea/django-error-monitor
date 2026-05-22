"""Logging handler that records logger.error(..., exc_info=True) into ErrorLog."""
import logging

logger = logging.getLogger(__name__)


class ErrorLogHandler(logging.Handler):
    """Capture log records with exc_info into the monitoring DB.

    Only processes records WITH exc_info (otherwise it's just a message, not an exception).
    Records without exc_info pass through untouched — use the middleware for request-scoped capture.
    """

    def emit(self, record):
        if not record.exc_info:
            return
        try:
            # Defer import so this handler can be referenced from LOGGING dict before apps load
            from ai_monitoring.services import capture_exception
            from ai_monitoring.notifications import send_alert

            group, created, should_notify = capture_exception(
                record.exc_info,
                extra={"logger": record.name, "level": record.levelname},
            )
            if should_notify and group is not None:
                send_alert(group)
        except Exception:
            # Never let a bad logging call crash the process
            self.handleError(record)

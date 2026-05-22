"""Async tasks dispatched via django-q."""
import logging

from ai_monitoring.models import ErrorLog

logger = logging.getLogger(__name__)


def send_alert_task(group_id):
    """Re-fetch the group and send its alert email. Runs in django-q worker."""
    from ai_monitoring.notifications import send_alert
    try:
        group = ErrorLog.objects.get(pk=group_id)
    except ErrorLog.DoesNotExist:
        logger.warning("send_alert_task: ErrorLog %s not found", group_id)
        return
    send_alert(group)

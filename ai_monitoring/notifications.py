"""Email alerts for new/recurring error groups."""
import logging

from django.conf import settings
from django.core.mail import mail_admins
from django.urls import reverse, NoReverseMatch

from ai_monitoring.models import ErrorLog
from ai_monitoring.services import mark_notified

logger = logging.getLogger(__name__)


def send_alert(group: ErrorLog):
    """Send an alert email for this error group via mail_admins."""
    if not getattr(settings, "ADMINS", None):
        logger.debug("No ADMINS configured; skipping alert for group %s", group.pk)
        return

    subject = f"Error: {group.exception_type} ({group.occurrence_count}x) — {group.message[:80]}"

    try:
        admin_url = reverse(
            "admin:ai_monitoring_errorlog_change", args=[group.pk]
        )
        base = getattr(settings, "SITE_URL", "") or ""
        admin_link = f"{base}{admin_url}" if base else admin_url
    except NoReverseMatch:
        admin_link = "(admin not available)"

    body = (
        f"Exception: {group.exception_type}\n"
        f"Message:   {group.message}\n"
        f"Count:     {group.occurrence_count}\n"
        f"First:     {group.first_seen}\n"
        f"Last:      {group.last_seen}\n"
        f"Path:      {group.sample_request_path or '(none)'}\n"
        f"Fingerprint: {group.fingerprint}\n\n"
        f"Admin:     {admin_link}\n\n"
        f"Sample traceback:\n{group.sample_traceback}\n"
    )

    try:
        mail_admins(subject, body, fail_silently=False)
        mark_notified(group)
    except Exception as exc:
        logger.exception("Failed to send error alert email: %s", exc)

"""Email alert + throttling tests."""
import sys
from datetime import timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from ai_monitoring.models import ErrorLog
from ai_monitoring.notifications import send_alert
from ai_monitoring.services import capture_exception, _should_notify


def _capture_value_error():
    try:
        raise ValueError("noti")
    except ValueError:
        return capture_exception(sys.exc_info())


@override_settings(ADMINS=[("Admin", "admin@example.com")])
class NotificationTests(TestCase):

    def test_send_alert_emails_admins(self):
        group, _, _ = _capture_value_error()
        mail.outbox = []
        send_alert(group)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertIn("ValueError", msg.subject)
        self.assertIn("noti", msg.body)
        self.assertIn("Fingerprint", msg.body)

    def test_send_alert_marks_notified(self):
        group, _, _ = _capture_value_error()
        self.assertIsNone(group.notified_at)
        send_alert(group)
        group.refresh_from_db()
        self.assertIsNotNone(group.notified_at)

    def test_should_notify_new_group(self):
        group = ErrorLog.objects.create(fingerprint="abc", exception_type="X")
        self.assertTrue(_should_notify(group, is_new_group=True))

    def test_should_notify_within_cooldown_returns_false(self):
        group = ErrorLog.objects.create(
            fingerprint="abc", exception_type="X",
            notified_at=timezone.now(),
        )
        self.assertFalse(_should_notify(group, is_new_group=False))

    def test_should_notify_after_cooldown_returns_true(self):
        past = timezone.now() - timedelta(hours=2)
        group = ErrorLog.objects.create(
            fingerprint="abc", exception_type="X", notified_at=past,
        )
        self.assertTrue(_should_notify(group, is_new_group=False))


@override_settings(ADMINS=[])
class NoAdminsTests(TestCase):
    def test_no_admins_no_email(self):
        group, _, _ = _capture_value_error()
        mail.outbox = []
        send_alert(group)
        self.assertEqual(len(mail.outbox), 0)

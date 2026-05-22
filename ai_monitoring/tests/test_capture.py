"""Core capture logic tests."""
import sys

from django.test import RequestFactory, TestCase

from ai_monitoring.models import ErrorLog, ErrorOccurrence
from ai_monitoring.services import capture_exception


def _raise_and_capture(factory_request=None, extra=None):
    try:
        raise ValueError("boom")
    except ValueError:
        return capture_exception(sys.exc_info(), request=factory_request, extra=extra)


def _raise_other():
    try:
        raise KeyError("missing")
    except KeyError:
        return capture_exception(sys.exc_info())


class CaptureExceptionTests(TestCase):

    def test_captures_into_new_group(self):
        group, created, should_notify = _raise_and_capture()
        self.assertIsNotNone(group)
        self.assertTrue(created)
        self.assertTrue(should_notify)
        self.assertEqual(group.exception_type, "ValueError")
        self.assertIn("boom", group.message)
        self.assertEqual(ErrorLog.objects.count(), 1)
        self.assertEqual(ErrorOccurrence.objects.count(), 1)

    def test_same_exception_groups_together(self):
        _raise_and_capture()
        _raise_and_capture()
        _raise_and_capture()
        self.assertEqual(ErrorLog.objects.count(), 1)
        self.assertEqual(ErrorOccurrence.objects.count(), 3)
        group = ErrorLog.objects.get()
        self.assertEqual(group.occurrence_count, 3)

    def test_different_exception_types_split_groups(self):
        _raise_and_capture()
        _raise_other()
        self.assertEqual(ErrorLog.objects.count(), 2)
        self.assertEqual(ErrorOccurrence.objects.count(), 2)

    def test_request_context_recorded(self):
        rf = RequestFactory()
        req = rf.post("/pay/?x=1", data={"field": "val"}, content_type="application/json")
        _raise_and_capture(factory_request=req)
        occ = ErrorOccurrence.objects.get()
        self.assertEqual(occ.request_method, "POST")
        self.assertEqual(occ.request_path, "/pay/")
        self.assertEqual(occ.request_query, "x=1")

    def test_sensitive_keys_redacted_in_extra(self):
        extra = {"api_key": "sk_test_x", "safe": "ok", "nested": {"password": "hunter2"}}
        _raise_and_capture(extra=extra)
        occ = ErrorOccurrence.objects.get()
        self.assertEqual(occ.extra["api_key"], "[REDACTED]")
        self.assertEqual(occ.extra["safe"], "ok")
        self.assertEqual(occ.extra["nested"]["password"], "[REDACTED]")

    def test_resolved_group_reopens_on_new_occurrence(self):
        group, _, _ = _raise_and_capture()
        group.resolved = True
        group.save(update_fields=["resolved"])

        group2, created, should_notify = _raise_and_capture()
        self.assertEqual(group2.pk, group.pk)
        self.assertFalse(created)
        self.assertFalse(group2.resolved)
        self.assertTrue(should_notify)  # re-opened → notify

    def test_returns_none_when_no_exception(self):
        group, created, should_notify = capture_exception((None, None, None))
        self.assertIsNone(group)
        self.assertFalse(created)
        self.assertFalse(should_notify)

"""Tests for the `monitoring_doctor` management command."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from ai_monitoring.models import ErrorLog


class MonitoringDoctorTests(TestCase):

    def test_doctor_runs_and_reports(self):
        out = StringIO()
        call_command("monitoring_doctor", stdout=out, no_color=True)
        report = out.getvalue()
        self.assertIn("django-error-monitor", report)
        self.assertIn("App installed", report)
        self.assertIn("Result:", report)

    def test_doctor_test_flag_captures_an_error(self):
        self.assertEqual(ErrorLog.objects.count(), 0)
        out = StringIO()
        call_command("monitoring_doctor", "--test", stdout=out, no_color=True)
        self.assertEqual(ErrorLog.objects.count(), 1)
        self.assertIn("Test capture", out.getvalue())

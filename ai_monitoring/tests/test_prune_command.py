"""prune_errorlogs management command."""
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from ai_monitoring.models import ErrorLog, ErrorOccurrence


class PruneCommandTests(TestCase):
    def setUp(self):
        self.group = ErrorLog.objects.create(fingerprint="abc", exception_type="X")
        # Old occurrence
        self.old = ErrorOccurrence.objects.create(group=self.group, request_path="/old/")
        ErrorOccurrence.objects.filter(pk=self.old.pk).update(
            timestamp=timezone.now() - timedelta(days=120)
        )
        # Recent
        self.recent = ErrorOccurrence.objects.create(group=self.group, request_path="/recent/")

    def test_deletes_old_occurrences(self):
        call_command("prune_errorlogs", "--occurrence-days=90")
        self.assertFalse(ErrorOccurrence.objects.filter(pk=self.old.pk).exists())
        self.assertTrue(ErrorOccurrence.objects.filter(pk=self.recent.pk).exists())

    def test_dry_run_deletes_nothing(self):
        out = StringIO()
        call_command("prune_errorlogs", "--occurrence-days=90", "--dry-run", stdout=out)
        self.assertEqual(ErrorOccurrence.objects.count(), 2)
        self.assertIn("dry-run", out.getvalue())

    def test_resolved_groups_deleted_when_requested(self):
        self.group.resolved = True
        self.group.save(update_fields=["resolved"])
        ErrorLog.objects.filter(pk=self.group.pk).update(
            last_seen=timezone.now() - timedelta(days=400)
        )
        call_command("prune_errorlogs", "--resolved-group-days=365")
        self.assertFalse(ErrorLog.objects.filter(pk=self.group.pk).exists())

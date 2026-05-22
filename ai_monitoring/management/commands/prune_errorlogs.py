"""Delete old ErrorOccurrence rows, and optionally resolved groups."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ai_monitoring.models import ErrorLog, ErrorOccurrence


class Command(BaseCommand):
    help = "Prune old ErrorOccurrence rows; keep groups."

    def add_arguments(self, parser):
        parser.add_argument(
            "--occurrence-days", type=int, default=90,
            help="Delete occurrences older than N days (default: 90).",
        )
        parser.add_argument(
            "--resolved-group-days", type=int, default=None,
            help="Also delete resolved groups untouched for N days. Omit to keep all groups.",
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        now = timezone.now()
        occ_cutoff = now - timedelta(days=opts["occurrence_days"])
        occ_qs = ErrorOccurrence.objects.filter(timestamp__lt=occ_cutoff)
        occ_count = occ_qs.count()

        if opts["dry_run"]:
            self.stdout.write(f"[dry-run] would delete {occ_count} occurrences older than {occ_cutoff.date()}")
        else:
            deleted, _ = occ_qs.delete()
            self.stdout.write(f"Deleted {deleted} occurrences older than {occ_cutoff.date()}")

        if opts["resolved_group_days"]:
            grp_cutoff = now - timedelta(days=opts["resolved_group_days"])
            grp_qs = ErrorLog.objects.filter(resolved=True, last_seen__lt=grp_cutoff)
            grp_count = grp_qs.count()
            if opts["dry_run"]:
                self.stdout.write(f"[dry-run] would delete {grp_count} resolved groups")
            else:
                deleted, _ = grp_qs.delete()
                self.stdout.write(f"Deleted {deleted} resolved groups")

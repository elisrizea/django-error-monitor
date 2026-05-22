"""Self-diagnostic for django-error-monitor.

    python manage.py monitoring_doctor          # health report
    python manage.py monitoring_doctor --test   # also capture a test error

Written to be read by a person *and* parsed by an AI assistant: every check
prints one line starting with [ OK ], [WARN] or [FAIL]; the command exits
non-zero if any check FAILs.
"""
import sys

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand

MIDDLEWARE_PATH = "ai_monitoring.middleware.ErrorCaptureMiddleware"
LINE = "-" * 56


class Command(BaseCommand):
    help = "Diagnose django-error-monitor: wiring, migrations, email and alerts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--test", action="store_true",
            help="Capture a harmless test error and confirm it was recorded.",
        )

    def handle(self, *args, **options):
        self.stdout.write("\ndjango-error-monitor — health check")
        self.stdout.write(LINE)

        self._failed = False
        self._warned = False

        # 1. App installed
        if apps.is_installed("ai_monitoring"):
            self._ok("App installed — 'ai_monitoring' is in INSTALLED_APPS")
        else:
            self._fail("App NOT installed — add 'ai_monitoring' to INSTALLED_APPS")

        # 2. Database tables / migrations
        from ai_monitoring.models import ErrorLog, ErrorOccurrence
        try:
            groups = ErrorLog.objects.count()
            occurrences = ErrorOccurrence.objects.count()
            self._ok(f"Database ready — migrations applied ({groups} error "
                     f"group(s), {occurrences} occurrence(s) recorded)")
        except Exception:
            self._fail("Database tables missing — run: python manage.py migrate")

        # 3. Middleware
        if MIDDLEWARE_PATH in list(getattr(settings, "MIDDLEWARE", []) or []):
            self._ok("Middleware — ErrorCaptureMiddleware is active")
        else:
            self._warn("Middleware NOT installed — unhandled request errors "
                       f"won't be caught. Add '{MIDDLEWARE_PATH}' to MIDDLEWARE.")

        # 4. Email alerts
        admins = getattr(settings, "ADMINS", None)
        backend = getattr(settings, "EMAIL_BACKEND", "") or ""
        if not admins:
            self._warn("Email alerts OFF — no ADMINS set. Errors are still "
                       "captured and visible in the admin; set ADMINS to get "
                       "alert emails.")
        elif backend.endswith("dummy.EmailBackend"):
            self._warn("Email alerts OFF — EMAIL_BACKEND is the dummy backend.")
        else:
            recipients = ", ".join(a[1] for a in admins)
            where = "console" if backend.endswith("console.EmailBackend") else "email"
            self._ok(f"Email alerts ON ({where}) — recipients: {recipients}")

        # 5. Alert delivery mode
        if apps.is_installed("django_q"):
            self._ok("Alert delivery — django-q detected; alerts sent in background")
        else:
            self._ok("Alert delivery — synchronous (install django-q for background)")

        # 6. Optional: capture a real test error
        if options["test"]:
            self.stdout.write(LINE)
            self._run_test()

        # Summary
        self.stdout.write(LINE)
        if self._failed:
            self.stdout.write(self.style.ERROR(
                "Result: FAILED — fix the [FAIL] items above, then re-run."))
            sys.exit(1)
        elif self._warned:
            self.stdout.write(self.style.WARNING(
                "Result: working, with warnings — capture is active; address "
                "[WARN] items to enable email alerts."))
        else:
            self.stdout.write(self.style.SUCCESS(
                "Result: all good — django-error-monitor is fully configured."))

    def _ok(self, msg):
        self.stdout.write(f"[ {self.style.SUCCESS('OK')} ]  {msg}")

    def _warn(self, msg):
        self._warned = True
        self.stdout.write(f"[{self.style.WARNING('WARN')}]  {msg}")

    def _fail(self, msg):
        self._failed = True
        self.stdout.write(f"[{self.style.ERROR('FAIL')}]  {msg}")

    def _run_test(self):
        from ai_monitoring.models import ErrorLog
        from ai_monitoring.services import capture_exception
        before = ErrorLog.objects.count()
        try:
            raise RuntimeError(
                "django-error-monitor self-test — this entry is safe to delete")
        except RuntimeError:
            group, _created, _notify = capture_exception(sys.exc_info())
        if group is not None and ErrorLog.objects.count() >= before:
            self._ok(f"Test capture — a test error was recorded (group #{group.pk}). "
                     "Open the Django admin -> Error monitoring to see it.")
        else:
            self._fail("Test capture FAILED — the test error was not recorded.")

"""Django system checks — surface mis-wiring automatically.

These run on every ``manage.py check`` and ``runserver``. They only ever emit
Warnings (never Errors): error capture keeps working even when the middleware
or email alerts are not configured, so nothing here should block startup.
"""
from django.conf import settings
from django.core.checks import Warning, register

MIDDLEWARE_PATH = "ai_monitoring.middleware.ErrorCaptureMiddleware"


@register()
def monitoring_configuration_checks(app_configs, **kwargs):
    issues = []

    if MIDDLEWARE_PATH not in list(getattr(settings, "MIDDLEWARE", []) or []):
        issues.append(Warning(
            "ErrorCaptureMiddleware is not installed — unhandled request "
            "exceptions will not be captured.",
            hint=f"Add '{MIDDLEWARE_PATH}' to MIDDLEWARE, near the end of the list.",
            id="ai_monitoring.W001",
        ))

    if not getattr(settings, "ADMINS", None):
        issues.append(Warning(
            "No ADMINS configured — errors are captured but no alert email is sent.",
            hint="Set ADMINS = [('Your Name', 'you@example.com')] to receive alerts.",
            id="ai_monitoring.W002",
        ))

    backend = getattr(settings, "EMAIL_BACKEND", "") or ""
    if backend.endswith("dummy.EmailBackend"):
        issues.append(Warning(
            "EMAIL_BACKEND is the dummy backend — alert emails are silently dropped.",
            hint="Configure a real EMAIL_BACKEND (e.g. SMTP) to receive error alerts.",
            id="ai_monitoring.W003",
        ))

    return issues

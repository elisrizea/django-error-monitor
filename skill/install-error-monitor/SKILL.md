---
name: install-error-monitor
description: Install and wire up the django-error-monitor package (in-database error capture, grouping, and email alerts — a self-hosted Sentry alternative) into a Django project. Use when the user wants error monitoring, exception tracking, or asks to "install django-error-monitor". Detects the project layout, asks plain-language questions, makes all edits, and verifies the result.
---

# Install django-error-monitor

Install the **django-error-monitor** package into the user's Django project — a
self-hosted error-capture tool: in-database exception capture, grouping, and email alerts.

The user should only need to *answer plain-language questions* — you do every file edit
and command. Be conversational; never show raw tracebacks or jargon — translate.

## Procedure

This mirrors the canonical runbook, `INSTALL.md`, in the django-error-monitor repo
(<https://github.com/elisrizea/django-error-monitor/blob/main/INSTALL.md>).

1. **Confirm** the target is a Django project (`manage.py` + a settings module). If not,
   stop and explain that this tool is for Django projects.
2. **Install the package** — detect the environment (Docker, Poetry, Pipenv, or plain
   pip) and install `django-error-monitor` the matching way; add it to the project's
   dependency file. Install from PyPI; fall back to
   `git+https://github.com/elisrizea/django-error-monitor` if needed.
3. **Add the app** — add `"ai_monitoring"` to `INSTALLED_APPS` in the correct settings
   file (ask if there are several).
4. **Add the middleware** — append `"ai_monitoring.middleware.ErrorCaptureMiddleware"`
   to `MIDDLEWARE`, near the end of the list.
5. **Ask about alerts**, in plain language:
   - *"Do you want to be emailed when your site hits an error? If so, what address?"*
     → set `ADMINS`. If the project has no working email setup, explain it simply, and
     either scaffold an SMTP block with placeholders or set the console email backend
     (`django.core.mail.backends.console.EmailBackend`) as a safe default.
   - Optionally: *"What is the site's public URL?"* → set `SITE_URL` for clickable
     admin links in alert emails.
6. **Migrate** — run `python manage.py migrate ai_monitoring` (inside the container if
   the project is dockerized).
7. **Verify** — run `python manage.py monitoring_doctor --test`, then read the result
   back to the user in plain language.
8. **Report** — tell the user what was done, that their errors now appear in
   **Django admin → Error monitoring**, and whether email alerts are on.

## Notes

- `django-q` is optional: if the project has it, alerts are sent in the background
  automatically; if not, they send synchronously. Nothing to configure either way.
- If anything is ambiguous (e.g. multiple settings files, no obvious dependency file),
  ask the user rather than guessing.
- The package is safe: capturing errors can never break the user's site.

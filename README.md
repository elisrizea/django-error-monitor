# django-error-monitor

**In-database error capture, grouping, and email alerts for Django — a self-hosted "Sentry-lite".**

Drop-in middleware. No external service, no SaaS account, no per-event billing. Unhandled
exceptions are captured into your own database, grouped so a recurring bug is one row (not
ten thousand), and emailed to you — rate-limited so an error storm can't flood your inbox.

- Package name **`django-error-monitor`** · imported as **`ai_monitoring`** · v0.1.0, 33 tests
- Not on PyPI yet: install from GitHub (below). Extracted from the monitoring app that runs in production on DBM AI's Django products
- License: **0BSD** — use, modify, sell, redistribute freely; no attribution required

## What it does

- **Captures** unhandled request exceptions (middleware) and `logger.error(..., exc_info=True)` (logging handler).
- **Groups** identical errors by a stable fingerprint (exception type + traceback shape); counts occurrences and keeps the latest sample plus per-occurrence request context.
- **Protects itself** — a rate-limit caps captures per fingerprint, and a circuit-breaker stops capture if the database is struggling. Capture failures never break the request.
- **Redacts** sensitive keys (password / token / api_key / secret / authorization) from captured data.
- **Alerts** by email on a new error, a re-occurrence after resolution, or after a 1-hour cooldown — synchronously, or in the background if `django-q` is installed.
- **Admin** — browse, search, filter, and resolve errors in the Django admin.

## Quick start (developers)

```bash
pip install git+https://github.com/elisrizea/django-error-monitor
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "ai_monitoring",
]

MIDDLEWARE = [
    # ... keep this near the end of the list ...
    "ai_monitoring.middleware.ErrorCaptureMiddleware",
]

# Where alert emails go (Django's standard setting):
ADMINS = [("Your Name", "you@example.com")]
```

```bash
python manage.py migrate
python manage.py monitoring_doctor   # verify the setup
```

That's it. Errors now land in **Admin → Error monitoring**.

## Install with an AI assistant (no coding)

You don't have to edit anything by hand. Open your Django project in **Claude Code** or
**OpenAI Codex** and ask it to install django-error-monitor:

- **Claude Code** — copy the bundled skill (`skill/install-error-monitor/`) into
  `~/.claude/skills/`, then say *"install django-error-monitor in this project."*
- **Codex / other agents** — say *"install django-error-monitor by following INSTALL.md
  from https://github.com/elisrizea/django-error-monitor."*

The assistant detects your project layout, asks a couple of plain-language questions
(e.g. where alerts should be emailed), makes every change, runs `monitoring_doctor --test`,
and shows you the result. Full runbook: [INSTALL.md](INSTALL.md).

## Configuration

All settings are optional — the package works with none of them.

| Setting | Effect | Default |
|---|---|---|
| `ADMINS` | Recipients of alert emails (standard Django setting). No `ADMINS` → capture still works, just no emails. | — |
| `EMAIL_BACKEND` + SMTP settings | How alert emails are sent (standard Django email config). | — |
| `SITE_URL` | Base URL prefixed to the admin link inside alert emails (e.g. `https://example.com`). | `""` |
| `django_q` in `INSTALLED_APPS` | If present, alert emails are dispatched via a django-q task instead of synchronously. | — |

## The `monitoring_doctor` command

```bash
python manage.py monitoring_doctor          # plain-language health report
python manage.py monitoring_doctor --test   # also capture a test error end-to-end
```

It checks: app installed, migrations applied, middleware wired, email configured, and the
alert delivery mode. It exits non-zero if anything is broken — handy for CI and for AI
assistants. The package also registers **Django system checks**, so `manage.py check` /
`runserver` warn you automatically if the middleware or email aren't configured.

## How capture & alerting work

- **Fingerprint** = exception type + the file/function of the top 5 traceback frames (line
  numbers excluded, so a group survives small code edits).
- **Rate limit** — at most 10 captures per fingerprint per 60s; excess occurrences are dropped.
- **Circuit breaker** — 20 capture failures in 60s opens the breaker for 5 minutes; capture
  is then skipped (fail-safe) so monitoring can never amplify an outage.
- **Alert cooldown** — at most one email per group per hour, plus an email when a resolved
  group recurs.

## Requirements

- Python ≥ 3.9
- Django ≥ 4.2
- `django-q` *(optional)* — background alert delivery: `pip install "django-error-monitor[async] @ git+https://github.com/elisrizea/django-error-monitor"`

## Running the tests

```bash
pip install Django
python runtests.py   # 33 tests, no external services needed
```

## License

[0BSD](LICENSE) — a gift to the community. Do whatever you like with it: use, modify,
sell, redistribute. No attribution required, no warranty.

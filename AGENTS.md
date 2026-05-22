# AGENTS.md

Guidance for AI assistants and contributors working **on the django-error-monitor
package itself**.

> To *install* the package into a Django project, follow [INSTALL.md](INSTALL.md) instead.

## Project layout

- `ai_monitoring/` — the Django app (the importable package; import name is stable).
  - `services.py` — capture core: fingerprint, redact, rate-limit gate, transactional write.
  - `middleware.py` — request-exception capture. `handlers.py` — logging handler.
  - `models.py` — `ErrorLog` (group) + `ErrorOccurrence` (single hit).
  - `ratelimit.py` — cache-based rate limit + circuit breaker (fail-open).
  - `notifications.py` / `tasks.py` — email alerts (synchronous, or via django-q).
  - `checks.py` — Django system checks. `admin.py` — admin UI.
  - `management/commands/` — `monitoring_doctor`, `prune_errorlogs`.
  - `tests/` — the test suite.
- `pyproject.toml` — packaging metadata. `runtests.py` — standalone test runner.

## Running the tests

```bash
python runtests.py
```

No project or database setup is needed — `runtests.py` configures an in-memory SQLite
Django and runs the `ai_monitoring` suite.

## Conventions

- Keep the app **self-contained** — no imports from any consuming project, and no
  hardcoded project names, URLs, emails, or secrets. All settings access goes through
  `getattr(settings, ..., default)`.
- Capture must **never break the host request** — failures are swallowed or fail open.
- Every change keeps `python runtests.py` green and adds tests for new behaviour.
- Stable public surface: the `ai_monitoring` import path and Django app label, the
  `ErrorCaptureMiddleware` path, and the model names.

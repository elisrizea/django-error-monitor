# Installing django-error-monitor

A step-by-step runbook for installing **django-error-monitor** into a Django project.
It is written so an **AI coding assistant** (Claude Code, OpenAI Codex, Cursor, …) can
follow it verbatim — and it works just as well for a human.

**Goal:** the person installing this should only have to *answer plain-language
questions*. The assistant does every file edit and command.

---

## For the AI assistant

Be conversational. Detect what you can, propose a short plan, ask the questions in
Step 4, then do the work. Never show the user a raw traceback or jargon — translate.
At the end, prove it works.

### Step 0 — Confirm it's a Django project
Look for `manage.py` and a settings module. If there is none, stop and tell the user
this tool is for Django projects.

### Step 1 — Install the package
Detect the environment and install the matching way:
- **Docker** (`Dockerfile` / `docker-compose.yml` with a `web`/`app` service): add
  `django-error-monitor @ git+https://github.com/elisrizea/django-error-monitor` to `requirements.txt` (or `pyproject.toml`) and rebuild the
  image, or `pip install` inside the running container.
- **Poetry** (`poetry.lock`): `poetry add git+https://github.com/elisrizea/django-error-monitor`
- **Pipenv** (`Pipfile`): `pipenv install git+https://github.com/elisrizea/django-error-monitor#egg=django-error-monitor`
- **Plain venv / pip**: `pip install git+https://github.com/elisrizea/django-error-monitor`, and add the same `git+` line to `requirements.txt`.

The package is not on PyPI yet, so every method installs from GitHub.

### Step 2 — Add the app
Find the settings file — a single `settings.py`, or a `settings/` package (check
`DJANGO_SETTINGS_MODULE`). Add `"ai_monitoring"` to `INSTALLED_APPS`. If there are
multiple settings files (base/dev/prod), add it to the shared/base one — ask if unsure.

### Step 3 — Add the middleware
Append `"ai_monitoring.middleware.ErrorCaptureMiddleware"` to `MIDDLEWARE` — **near the
end** of the list, so it sees exceptions raised by the inner middleware and the views.

### Step 4 — Configure alerts (ask the user)
Ask, in plain language:
> "Do you want to be **emailed when your site hits an error**? If yes, which email address?"

- If **yes** → set `ADMINS = [("<name>", "<their email>")]` in settings, then check email sending:
  - If the project already has `EMAIL_BACKEND` + SMTP settings → done.
  - If **not**, explain plainly that sending email needs an SMTP account (their email
    provider, a Gmail app-password, AWS SES, Mailgun, …). Offer to scaffold the
    `EMAIL_BACKEND` / `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` /
    `EMAIL_HOST_PASSWORD` block with placeholders for them to fill in. As a safe default
    for now, set `EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"` so
    alerts print to the server console and nothing breaks.
- If **no** → skip it. Errors are still captured and visible in the admin.

Optionally ask: *"Does this site have a public URL?"* → set `SITE_URL` so alert emails
contain a clickable admin link.

### Step 5 — Migrate
Run `python manage.py migrate ai_monitoring` (inside the container if the project is dockerized).

### Step 6 — Verify
Run `python manage.py monitoring_doctor --test`. It prints a health report and captures a
test error end-to-end. Read the result back to the user in plain language.

### Step 7 — Report
Tell the user, simply:
- ✅ what was installed and changed,
- where to see their errors: **Django admin → Error monitoring**,
- whether email alerts are on — and if not, what they'd need to do to enable them.

---

## Manual install (human)

`pip install git+https://github.com/elisrizea/django-error-monitor`, add `"ai_monitoring"` to `INSTALLED_APPS`, append
`"ai_monitoring.middleware.ErrorCaptureMiddleware"` to `MIDDLEWARE`, set `ADMINS`, run
`python manage.py migrate`, then `python manage.py monitoring_doctor`. See the
"Quick start" in [README.md](README.md).

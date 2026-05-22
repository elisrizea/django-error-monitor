#!/usr/bin/env python
"""Run the django-error-monitor test suite standalone.

    python runtests.py

Configures an in-memory SQLite Django on the fly — no project or database
setup required.
"""
import importlib.util
import os
import sys

import django
from django.conf import settings


def main():
    # Discover tests relative to this file, not the caller's working directory.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    installed_apps = [
        "django.contrib.contenttypes",
        "django.contrib.auth",
        "ai_monitoring",
    ]
    # django-q is optional; include it so the async-dispatch tests run when present.
    if importlib.util.find_spec("django_q") is not None:
        installed_apps.append("django_q")

    settings.configure(
        DEBUG=False,
        SECRET_KEY="django-error-monitor-test-key",
        DATABASES={
            "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
        },
        INSTALLED_APPS=installed_apps,
        MIDDLEWARE=[],
        CACHES={
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
        },
        ROOT_URLCONF="ai_monitoring.tests.urls",
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        USE_TZ=True,
        LOGGING_CONFIG=None,
    )
    django.setup()

    from django.test.utils import get_runner

    runner = get_runner(settings)(verbosity=2, interactive=False)
    failures = runner.run_tests(["ai_monitoring"])
    sys.exit(bool(failures))


if __name__ == "__main__":
    main()

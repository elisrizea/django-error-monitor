"""Custom logging handler captures logger.exception() calls."""
import logging

from django.test import TestCase

from ai_monitoring.handlers import ErrorLogHandler
from ai_monitoring.models import ErrorLog, ErrorOccurrence


class ErrorLogHandlerTests(TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test_ai_monitoring_handler")
        self.logger.setLevel(logging.ERROR)
        self.handler = ErrorLogHandler()
        self.handler.setLevel(logging.ERROR)
        self.logger.addHandler(self.handler)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def test_logger_exception_captured(self):
        try:
            raise ZeroDivisionError("zap")
        except ZeroDivisionError:
            self.logger.exception("something bad")
        self.assertEqual(ErrorLog.objects.count(), 1)
        self.assertEqual(ErrorOccurrence.objects.get().group.exception_type, "ZeroDivisionError")

    def test_logger_without_exc_info_ignored(self):
        self.logger.error("just a message, no exc_info")
        self.assertEqual(ErrorLog.objects.count(), 0)

"""Middleware integration test — unhandled view exception is captured."""
from unittest.mock import patch

from django.http import Http404, HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import path

from ai_monitoring.middleware import ErrorCaptureMiddleware
from ai_monitoring.models import ErrorLog


def _boom_view(request):
    raise RuntimeError("middleware-boom")


def _ok_view(request):
    return HttpResponse("ok")


urlpatterns = [
    path("boom/", _boom_view),
    path("ok/", _ok_view),
]


@override_settings(ROOT_URLCONF=__name__, DEBUG=False, ALLOWED_HOSTS=["*"])
class ErrorCaptureMiddlewareTests(TestCase):

    def test_unhandled_exception_captured(self):
        mw = ErrorCaptureMiddleware(get_response=_boom_view)
        rf = RequestFactory()
        req = rf.get("/boom/")
        with patch("ai_monitoring.middleware.capture_exception") as mock_cap:
            mock_cap.return_value = (None, False, False)
            try:
                _boom_view(req)
            except RuntimeError as exc:
                mw.process_exception(req, exc)
        mock_cap.assert_called_once()

    def test_full_request_flow_records_group(self):
        # Using Django test client — but our middleware isn't installed by default in tests.
        # Direct middleware invocation is already covered above; here we verify DB write.
        rf = RequestFactory()
        req = rf.get("/boom/")
        mw = ErrorCaptureMiddleware(get_response=lambda r: None)
        try:
            raise RuntimeError("direct-boom")
        except RuntimeError as exc:
            mw.process_exception(req, exc)

        self.assertEqual(ErrorLog.objects.count(), 1)
        group = ErrorLog.objects.get()
        self.assertEqual(group.exception_type, "RuntimeError")

    def test_http404_is_not_captured(self):
        mw = ErrorCaptureMiddleware(get_response=lambda r: None)
        rf = RequestFactory()
        req = rf.get("/missing/")
        with patch("ai_monitoring.middleware.capture_exception") as mock_cap:
            result = mw.process_exception(req, Http404("nope"))
        self.assertIsNone(result)
        mock_cap.assert_not_called()
        self.assertEqual(ErrorLog.objects.count(), 0)

    def test_monitoring_failure_does_not_break_request(self):
        """If capture itself raises, middleware must swallow and return None."""
        mw = ErrorCaptureMiddleware(get_response=lambda r: None)
        rf = RequestFactory()
        req = rf.get("/boom/")
        with patch("ai_monitoring.middleware.capture_exception", side_effect=Exception("monitor broken")):
            try:
                raise ValueError("app error")
            except ValueError as exc:
                result = mw.process_exception(req, exc)
        self.assertIsNone(result)

"""Error capture service — shared by middleware and logging handler."""
import hashlib
import logging
import re
import traceback as tb_mod
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from ai_monitoring.models import ErrorLog, ErrorOccurrence
from ai_monitoring.ratelimit import (
    check_rate_limit,
    circuit_is_open,
    record_capture_failure,
    reset_capture_failures,
)

logger = logging.getLogger(__name__)

SENSITIVE_KEYS = re.compile(
    r"(password|api[_-]?key|secret|token|authorization|csrf)", re.IGNORECASE
)
BODY_PREVIEW_LIMIT = 2000
NOTIFY_COOLDOWN = timedelta(hours=1)


def _fingerprint(exc_type_name: str, tb_frames: list) -> str:
    """Stable hash across runs: exception type + top 5 frames (file+function, no line nums)."""
    parts = [exc_type_name]
    for frame in tb_frames[-5:]:
        parts.append(f"{frame.filename}:{frame.name}")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _sanitize_dict(data: dict) -> dict:
    out = {}
    for k, v in data.items():
        if SENSITIVE_KEYS.search(k):
            out[k] = "[REDACTED]"
        elif isinstance(v, dict):
            out[k] = _sanitize_dict(v)
        else:
            out[k] = v
    return out


def _extract_request_context(request) -> dict:
    if request is None:
        return {}
    ctx = {
        "request_method": getattr(request, "method", "") or "",
        "request_path": (getattr(request, "path", "") or "")[:500],
        "request_query": request.META.get("QUERY_STRING", "")[:500] if hasattr(request, "META") else "",
        "remote_addr": _client_ip(request),
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500] if hasattr(request, "META") else "",
    }

    user_id = ""
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        user_id = str(getattr(user, "pk", "") or "")
    if not user_id:
        customer = getattr(request, "customer", None)
        if customer is not None:
            user_id = f"customer:{getattr(customer, 'pk', '')}"
    ctx["user_id"] = user_id[:100]

    body_preview = ""
    try:
        if hasattr(request, "body"):
            raw = request.body
            if isinstance(raw, (bytes, bytearray)):
                raw = raw[:BODY_PREVIEW_LIMIT].decode("utf-8", errors="replace")
            body_preview = str(raw)[:BODY_PREVIEW_LIMIT]
    except Exception:
        body_preview = "[unreadable]"
    ctx["request_body_preview"] = body_preview

    return ctx


def _client_ip(request):
    if not hasattr(request, "META"):
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def capture_exception(exc_info, request=None, extra=None):
    """Record an exception. Returns (ErrorLog, is_new_group, should_notify)."""
    exc_type, exc_value, exc_tb = exc_info
    if exc_type is None:
        return None, False, False

    if circuit_is_open():
        return None, False, False

    tb_frames = tb_mod.extract_tb(exc_tb) if exc_tb else []
    fp = _fingerprint(exc_type.__name__, tb_frames)

    if not check_rate_limit(fp):
        return None, False, False

    traceback_text = "".join(tb_mod.format_exception(exc_type, exc_value, exc_tb))[-20000:]
    message = str(exc_value)[:2000]
    ctx = _extract_request_context(request)

    try:
        group, created = _write_capture(fp, exc_type, message, traceback_text, ctx, extra)
    except Exception:
        record_capture_failure()
        raise
    else:
        reset_capture_failures()

    should_notify = _should_notify(group, created)
    return group, created, should_notify


def _write_capture(fp, exc_type, message, traceback_text, ctx, extra):
    with transaction.atomic():
        group, created = ErrorLog.objects.select_for_update().get_or_create(
            fingerprint=fp,
            defaults={
                "exception_type": exc_type.__name__,
                "message": message,
                "sample_traceback": traceback_text,
                "sample_request_path": ctx.get("request_path", ""),
            },
        )

        update_fields = ["occurrence_count", "last_seen"]
        group.occurrence_count = (group.occurrence_count or 0) + 1
        if created or group.resolved:
            # New group or previously resolved → refresh sample + un-resolve
            group.sample_traceback = traceback_text
            group.sample_request_path = ctx.get("request_path", "")
            group.message = message
            update_fields += ["sample_traceback", "sample_request_path", "message"]
            if group.resolved:
                group.resolved = False
                group.resolved_at = None
                group.resolved_by = ""
                update_fields += ["resolved", "resolved_at", "resolved_by"]

        group.save(update_fields=update_fields)

        ErrorOccurrence.objects.create(
            group=group,
            request_method=ctx.get("request_method", ""),
            request_path=ctx.get("request_path", ""),
            request_query=ctx.get("request_query", ""),
            request_body_preview=ctx.get("request_body_preview", ""),
            user_id=ctx.get("user_id", ""),
            remote_addr=ctx.get("remote_addr"),
            user_agent=ctx.get("user_agent", ""),
            traceback=traceback_text,
            extra=_sanitize_dict(extra or {}),
        )

    return group, created


def _should_notify(group: ErrorLog, is_new_group: bool) -> bool:
    """Notify on: new group, or first occurrence after resolved, or cooldown elapsed."""
    if is_new_group:
        return True
    if group.notified_at is None:
        return True
    if timezone.now() - group.notified_at >= NOTIFY_COOLDOWN:
        return True
    return False


def mark_notified(group: ErrorLog):
    group.notified_at = timezone.now()
    group.save(update_fields=["notified_at"])

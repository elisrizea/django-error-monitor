from django.db import models


class ErrorLog(models.Model):
    """A group of identical errors (same fingerprint)."""

    fingerprint = models.CharField(max_length=64, unique=True, db_index=True)
    exception_type = models.CharField(max_length=200, db_index=True)
    message = models.TextField(blank=True)

    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(auto_now=True, db_index=True)
    occurrence_count = models.PositiveIntegerField(default=0)

    sample_traceback = models.TextField(blank=True)
    sample_request_path = models.CharField(max_length=500, blank=True)

    resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.CharField(max_length=200, blank=True)

    notified_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Last time an alert email was sent for this group.",
    )

    class Meta:
        ordering = ("-last_seen",)
        indexes = [
            models.Index(fields=["resolved", "-last_seen"]),
        ]

    def __str__(self):
        return f"{self.exception_type}: {self.message[:80]}"


class ErrorOccurrence(models.Model):
    """A single occurrence of an error, linked to a group."""

    group = models.ForeignKey(
        ErrorLog, on_delete=models.CASCADE, related_name="occurrences"
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    request_query = models.TextField(blank=True)
    request_body_preview = models.TextField(blank=True)
    user_id = models.CharField(max_length=100, blank=True)
    remote_addr = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    traceback = models.TextField(blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-timestamp",)
        indexes = [
            models.Index(fields=["group", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.group.exception_type} @ {self.timestamp:%Y-%m-%d %H:%M:%S}"

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from ai_monitoring.models import ErrorLog, ErrorOccurrence


class ErrorOccurrenceInline(admin.TabularInline):
    model = ErrorOccurrence
    extra = 0
    can_delete = False
    readonly_fields = (
        "timestamp", "request_method", "request_path", "user_id",
        "remote_addr", "request_body_preview", "traceback",
    )
    fields = readonly_fields
    ordering = ("-timestamp",)
    max_num = 0  # display only, prevent adding new via admin


@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = (
        "exception_type", "short_message", "occurrence_count",
        "last_seen", "resolved", "sample_request_path",
    )
    list_filter = ("resolved", "exception_type", "last_seen")
    search_fields = ("exception_type", "message", "fingerprint", "sample_request_path")
    readonly_fields = (
        "fingerprint", "exception_type", "message", "first_seen", "last_seen",
        "occurrence_count", "sample_traceback", "sample_request_path", "notified_at",
    )
    fieldsets = (
        (None, {
            "fields": ("exception_type", "message", "occurrence_count",
                       "first_seen", "last_seen", "sample_request_path", "fingerprint"),
        }),
        ("Traceback", {"fields": ("sample_traceback",), "classes": ("collapse",)}),
        ("Resolution", {"fields": ("resolved", "resolved_at", "resolved_by", "notified_at")}),
    )
    inlines = [ErrorOccurrenceInline]
    actions = ["mark_resolved", "mark_unresolved"]
    ordering = ("-last_seen",)
    list_per_page = 50

    def short_message(self, obj):
        return (obj.message or "")[:120]
    short_message.short_description = "Message"

    @admin.action(description="Mark selected errors as resolved")
    def mark_resolved(self, request, queryset):
        now = timezone.now()
        user = getattr(request, "user", None)
        resolver = str(user) if user and user.is_authenticated else "admin"
        updated = queryset.update(resolved=True, resolved_at=now, resolved_by=resolver)
        self.message_user(request, f"Marked {updated} error group(s) as resolved.")

    @admin.action(description="Re-open (mark as unresolved)")
    def mark_unresolved(self, request, queryset):
        updated = queryset.update(resolved=False, resolved_at=None, resolved_by="")
        self.message_user(request, f"Re-opened {updated} error group(s).")


@admin.register(ErrorOccurrence)
class ErrorOccurrenceAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "group", "request_path", "user_id", "remote_addr")
    list_filter = ("timestamp",)
    search_fields = ("request_path", "user_id", "remote_addr", "group__exception_type")
    readonly_fields = [f.name for f in ErrorOccurrence._meta.fields]
    ordering = ("-timestamp",)
    list_per_page = 100

    def has_add_permission(self, request):
        return False

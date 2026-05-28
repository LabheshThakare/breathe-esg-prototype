import json
from collections import Counter

from django.db.models import Count, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from .models import AuditEvent, IngestionRun, NormalizedActivity, RawRecord, Tenant


DEFAULT_TENANT_SLUG = "demo-enterprise"


def tenant_from_request(request):
    slug = request.GET.get("tenant", DEFAULT_TENANT_SLUG)
    return Tenant.objects.filter(slug=slug).first()


def tenant_or_404(request):
    tenant = tenant_from_request(request)
    if tenant:
        return tenant, None
    return None, JsonResponse({"error": "tenant_not_found"}, status=404)


def decimal_or_none(value):
    return str(value) if value is not None else None


def date_or_none(value):
    return value.isoformat() if value else None


def facility_payload(facility):
    if not facility:
        return None
    return {
        "id": facility.id,
        "facility_code": facility.facility_code,
        "name": facility.name,
        "country": facility.country,
        "region": facility.region,
    }


def activity_summary(activity):
    return {
        "id": activity.id,
        "source_record_id": activity.source_record_id,
        "source_type": activity.source_type,
        "source_name": activity.source_connection.name,
        "activity_category": activity.activity_category,
        "scope": activity.scope,
        "ghg_category": activity.ghg_category,
        "facility": facility_payload(activity.facility),
        "activity_date": date_or_none(activity.activity_date),
        "period_start": date_or_none(activity.period_start),
        "period_end": date_or_none(activity.period_end),
        "supplier": activity.supplier,
        "description": activity.description,
        "activity_value": decimal_or_none(activity.activity_value),
        "activity_unit": activity.activity_unit,
        "normalized_value": decimal_or_none(activity.normalized_value),
        "normalized_unit": activity.normalized_unit,
        "co2e_kg": decimal_or_none(activity.co2e_kg),
        "emission_factor_key": activity.emission_factor_key,
        "quality_flags": activity.quality_flags,
        "review_status": activity.review_status,
        "approved_by": activity.approved_by,
        "approved_at": date_or_none(activity.approved_at),
        "locked_at": date_or_none(activity.locked_at),
        "created_at": date_or_none(activity.created_at),
        "updated_at": date_or_none(activity.updated_at),
    }


def audit_event_payload(event):
    return {
        "id": event.id,
        "event_type": event.event_type,
        "actor": event.actor,
        "before": event.before,
        "after": event.after,
        "created_at": date_or_none(event.created_at),
    }


def activity_detail_payload(activity):
    payload = activity_summary(activity)
    payload.update(
        {
            "source_payload": activity.source_payload,
            "edited_payload": activity.edited_payload,
            "raw_record": {
                "id": activity.raw_record.id,
                "source_row_id": activity.raw_record.source_row_id,
                "status": activity.raw_record.status,
                "payload_hash": activity.raw_record.payload_hash,
                "validation_errors": activity.raw_record.validation_errors,
                "payload": activity.raw_record.payload,
            },
            "audit_events": [
                audit_event_payload(event)
                for event in activity.audit_events.all().order_by("-created_at")
            ],
        }
    )
    return payload


def run_payload(run):
    return {
        "id": run.id,
        "source_type": run.source_connection.source_type,
        "source_name": run.source_connection.name,
        "original_filename": run.original_filename,
        "status": run.status,
        "total_rows": run.total_rows,
        "succeeded_rows": run.succeeded_rows,
        "failed_rows": run.failed_rows,
        "started_at": date_or_none(run.started_at),
        "completed_at": date_or_none(run.completed_at),
        "notes": run.notes,
    }


def failed_record_payload(raw):
    return {
        "id": raw.id,
        "source_type": raw.ingestion_run.source_connection.source_type,
        "source_name": raw.ingestion_run.source_connection.name,
        "ingestion_run_id": raw.ingestion_run_id,
        "source_row_id": raw.source_row_id,
        "status": raw.status,
        "validation_errors": raw.validation_errors,
        "payload": raw.payload,
        "created_at": date_or_none(raw.created_at),
    }


def filtered_activities(request, tenant):
    queryset = (
        NormalizedActivity.objects.filter(tenant=tenant)
        .select_related("source_connection", "facility", "raw_record")
        .order_by("-created_at", "-id")
    )

    source_type = request.GET.get("source_type")
    scope = request.GET.get("scope")
    review_status = request.GET.get("review_status")
    flag = request.GET.get("flag")
    search = request.GET.get("search")

    if source_type:
        queryset = queryset.filter(source_type=source_type)
    if scope:
        queryset = queryset.filter(scope=scope)
    if review_status:
        queryset = queryset.filter(review_status=review_status)
    if flag:
        matching_ids = [activity.id for activity in queryset if flag in activity.quality_flags]
        queryset = queryset.filter(id__in=matching_ids)
    if search:
        queryset = queryset.filter(description__icontains=search) | queryset.filter(supplier__icontains=search)

    return queryset


@require_GET
def overview(request):
    tenant, error = tenant_or_404(request)
    if error:
        return error
    return JsonResponse(
        {
            "app": "Breathe ESG ingestion API",
            "status": "review-api-ready",
            "tenant": {"id": tenant.id, "slug": tenant.slug, "name": tenant.name},
            "endpoints": [
                "/api/dashboard/",
                "/api/activities/",
                "/api/activities/<id>/",
                "/api/activities/<id>/approve/",
                "/api/activities/<id>/reject/",
                "/api/activities/<id>/lock/",
                "/api/failed-records/",
                "/api/runs/",
            ],
        }
    )


@require_GET
def dashboard(request):
    tenant, error = tenant_or_404(request)
    if error:
        return error

    activities = NormalizedActivity.objects.filter(tenant=tenant)
    raw_records = RawRecord.objects.filter(tenant=tenant)
    runs = IngestionRun.objects.filter(tenant=tenant)
    flags = Counter(flag for flags in activities.values_list("quality_flags", flat=True) for flag in flags)

    return JsonResponse(
        {
            "tenant": {"id": tenant.id, "slug": tenant.slug, "name": tenant.name},
            "totals": {
                "ingestion_runs": runs.count(),
                "raw_records": raw_records.count(),
                "failed_raw_records": raw_records.filter(status=RawRecord.FAILED).count(),
                "normalized_activities": activities.count(),
                "flagged_activities": sum(1 for flags_value in activities.values_list("quality_flags", flat=True) if flags_value),
                "co2e_kg": decimal_or_none(activities.aggregate(total=Sum("co2e_kg"))["total"]),
            },
            "by_source": list(activities.values("source_type").annotate(count=Count("id")).order_by("source_type")),
            "by_scope": list(activities.values("scope").annotate(count=Count("id")).order_by("scope")),
            "by_review_status": list(
                activities.values("review_status").annotate(count=Count("id")).order_by("review_status")
            ),
            "quality_flags": [{"flag": flag, "count": count} for flag, count in sorted(flags.items())],
            "failed_by_source": list(
                raw_records.filter(status=RawRecord.FAILED)
                .values("ingestion_run__source_connection__source_type")
                .annotate(count=Count("id"))
                .order_by("ingestion_run__source_connection__source_type")
            ),
        }
    )


@require_GET
def activities(request):
    tenant, error = tenant_or_404(request)
    if error:
        return error

    queryset = filtered_activities(request, tenant)
    limit = min(int(request.GET.get("limit", "100")), 250)
    return JsonResponse(
        {
            "count": queryset.count(),
            "results": [activity_summary(activity) for activity in queryset[:limit]],
        }
    )


@require_GET
def activity_detail(request, activity_id):
    tenant, error = tenant_or_404(request)
    if error:
        return error

    activity = (
        NormalizedActivity.objects.filter(tenant=tenant, id=activity_id)
        .select_related("source_connection", "facility", "raw_record")
        .prefetch_related("audit_events")
        .first()
    )
    if not activity:
        return JsonResponse({"error": "activity_not_found"}, status=404)
    return JsonResponse(activity_detail_payload(activity))


@csrf_exempt
@require_http_methods(["POST"])
def approve_activity(request, activity_id):
    return update_review_status(request, activity_id, NormalizedActivity.APPROVED, AuditEvent.APPROVED)


@csrf_exempt
@require_http_methods(["POST"])
def reject_activity(request, activity_id):
    return update_review_status(request, activity_id, NormalizedActivity.REJECTED, AuditEvent.REJECTED)


@csrf_exempt
@require_http_methods(["POST"])
def lock_activity(request, activity_id):
    tenant, error = tenant_or_404(request)
    if error:
        return error

    activity = NormalizedActivity.objects.filter(tenant=tenant, id=activity_id).select_related("source_connection").first()
    if not activity:
        return JsonResponse({"error": "activity_not_found"}, status=404)
    if activity.review_status == NormalizedActivity.LOCKED:
        return JsonResponse(activity_summary(activity))
    if activity.review_status != NormalizedActivity.APPROVED:
        return JsonResponse({"error": "activity_must_be_approved_before_lock"}, status=400)

    actor = request_actor(request)
    before = review_snapshot(activity)
    activity.review_status = NormalizedActivity.LOCKED
    activity.locked_at = timezone.now()
    activity.save(update_fields=["review_status", "locked_at", "updated_at"])
    create_review_event(activity, AuditEvent.LOCKED, actor, before)
    return JsonResponse(activity_summary(activity))


def update_review_status(request, activity_id, status, event_type):
    tenant, error = tenant_or_404(request)
    if error:
        return error

    activity = NormalizedActivity.objects.filter(tenant=tenant, id=activity_id).select_related("source_connection").first()
    if not activity:
        return JsonResponse({"error": "activity_not_found"}, status=404)
    if activity.review_status == NormalizedActivity.LOCKED:
        return JsonResponse({"error": "activity_is_locked"}, status=409)

    actor = request_actor(request)
    before = review_snapshot(activity)
    activity.review_status = status
    if status == NormalizedActivity.APPROVED:
        activity.approved_by = actor
        activity.approved_at = timezone.now()
    if status == NormalizedActivity.REJECTED:
        activity.approved_by = ""
        activity.approved_at = None
    activity.save(update_fields=["review_status", "approved_by", "approved_at", "updated_at"])
    create_review_event(activity, event_type, actor, before)
    return JsonResponse(activity_summary(activity))


def request_actor(request):
    if not request.body:
        return "demo analyst"
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return "demo analyst"
    return payload.get("actor") or "demo analyst"


def review_snapshot(activity):
    return {
        "review_status": activity.review_status,
        "approved_by": activity.approved_by,
        "approved_at": date_or_none(activity.approved_at),
        "locked_at": date_or_none(activity.locked_at),
    }


def create_review_event(activity, event_type, actor, before):
    AuditEvent.objects.create(
        tenant=activity.tenant,
        normalized_activity=activity,
        event_type=event_type,
        actor=actor,
        before=before,
        after=review_snapshot(activity),
    )


@require_GET
def failed_records(request):
    tenant, error = tenant_or_404(request)
    if error:
        return error

    queryset = (
        RawRecord.objects.filter(tenant=tenant, status=RawRecord.FAILED)
        .select_related("ingestion_run__source_connection")
        .order_by("-created_at", "-id")
    )
    source_type = request.GET.get("source_type")
    if source_type:
        queryset = queryset.filter(ingestion_run__source_connection__source_type=source_type)

    return JsonResponse(
        {
            "count": queryset.count(),
            "results": [failed_record_payload(record) for record in queryset],
        }
    )


@require_GET
def runs(request):
    tenant, error = tenant_or_404(request)
    if error:
        return error

    queryset = IngestionRun.objects.filter(tenant=tenant).select_related("source_connection").order_by("-started_at")
    source_type = request.GET.get("source_type")
    if source_type:
        queryset = queryset.filter(source_connection__source_type=source_type)

    return JsonResponse(
        {
            "count": queryset.count(),
            "results": [run_payload(run) for run in queryset],
        }
    )

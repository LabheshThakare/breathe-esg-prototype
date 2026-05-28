from django.contrib import admin

from .models import (
    AuditEvent,
    EmissionFactor,
    Facility,
    IngestionRun,
    NormalizedActivity,
    RawRecord,
    SourceConnection,
    Tenant,
)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("facility_code", "name", "tenant", "country", "region", "utility_account")
    list_filter = ("tenant", "country")
    search_fields = ("facility_code", "name", "utility_account")


@admin.register(SourceConnection)
class SourceConnectionAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "source_type", "ingestion_mechanism", "created_at")
    list_filter = ("tenant", "source_type")
    search_fields = ("name",)


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "source_connection", "status", "total_rows", "succeeded_rows", "failed_rows", "started_at")
    list_filter = ("tenant", "status", "source_connection__source_type")
    search_fields = ("original_filename", "notes")


@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "ingestion_run", "source_row_id", "status", "created_at")
    list_filter = ("tenant", "status")
    search_fields = ("source_row_id", "payload_hash")


@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ("key", "label", "tenant", "factor_value", "factor_unit", "source")
    list_filter = ("tenant",)
    search_fields = ("key", "label", "source")


@admin.register(NormalizedActivity)
class NormalizedActivityAdmin(admin.ModelAdmin):
    list_display = ("source_record_id", "tenant", "source_type", "scope", "activity_category", "review_status", "co2e_kg")
    list_filter = ("tenant", "source_type", "scope", "review_status")
    search_fields = ("source_record_id", "supplier", "description")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "tenant", "normalized_activity", "actor", "created_at")
    list_filter = ("tenant", "event_type")
    search_fields = ("actor",)

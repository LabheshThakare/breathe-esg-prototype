import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ingest.models import AuditEvent, IngestionRun, NormalizedActivity, RawRecord, SourceConnection, Tenant
from ingest.normalizers import (
    NormalizationError,
    distance_lookup,
    normalize_sap_row,
    normalize_travel_row,
    normalize_utility_row,
    row_hash,
    sap_plant_map,
)


class Command(BaseCommand):
    help = "Load the sample CSV files into raw records and normalized activities."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-slug", default="demo-enterprise")
        parser.add_argument(
            "--keep-existing",
            action="store_true",
            help="Do not clear previous sample ingestion output before loading.",
        )

    def handle(self, *args, **options):
        tenant = Tenant.objects.filter(slug=options["tenant_slug"]).first()
        if not tenant:
            raise CommandError("Demo tenant not found. Run `python manage.py seed_foundation` first.")

        sources = list(SourceConnection.objects.filter(tenant=tenant).order_by("source_type"))
        if len(sources) < 3:
            raise CommandError("Expected seeded SAP, utility, and travel source connections. Run seed_foundation first.")

        if not options["keep_existing"]:
            self._clear_existing_sample_output(tenant, sources)

        totals = {"runs": 0, "raw": 0, "normalized": 0, "failed": 0}
        for source in sources:
            result = self._ingest_source(tenant, source)
            for key, value in result.items():
                totals[key] += value

        self.stdout.write(
            self.style.SUCCESS(
                "Ingested samples: "
                f"{totals['runs']} runs, {totals['raw']} raw rows, "
                f"{totals['normalized']} normalized activities, {totals['failed']} failed rows."
            )
        )

    def _clear_existing_sample_output(self, tenant, sources):
        runs = IngestionRun.objects.filter(tenant=tenant, source_connection__in=sources)
        activities = NormalizedActivity.objects.filter(tenant=tenant, ingestion_run__in=runs)
        AuditEvent.objects.filter(tenant=tenant, normalized_activity__in=activities).delete()
        activities.delete()
        RawRecord.objects.filter(tenant=tenant, ingestion_run__in=runs).delete()
        runs.delete()

    def _ingest_source(self, tenant, source):
        source_file = Path(settings.REPO_ROOT) / source.config["source_file"]
        if not source_file.exists():
            raise CommandError(f"Missing sample file: {source_file}")

        rows = self._read_rows(source_file)
        run = IngestionRun.objects.create(
            tenant=tenant,
            source_connection=source,
            original_filename=source_file.name,
            total_rows=len(rows),
        )

        normalized_count = 0
        failed_count = 0

        with transaction.atomic():
            for index, row in enumerate(rows, start=1):
                raw = RawRecord.objects.create(
                    tenant=tenant,
                    ingestion_run=run,
                    source_row_id=self._source_row_id(source, row, index),
                    payload=row,
                    payload_hash=row_hash(row),
                )

                try:
                    normalized = self._normalize(tenant, source, row)
                except NormalizationError as exc:
                    raw.status = RawRecord.FAILED
                    raw.validation_errors = [str(exc)]
                    raw.save(update_fields=["status", "validation_errors"])
                    failed_count += 1
                    continue

                activity = NormalizedActivity.objects.create(
                    tenant=tenant,
                    source_connection=source,
                    ingestion_run=run,
                    raw_record=raw,
                    facility=normalized.facility,
                    source_record_id=normalized.source_record_id,
                    source_type=normalized.source_type,
                    activity_category=normalized.activity_category,
                    scope=normalized.scope,
                    ghg_category=normalized.ghg_category,
                    activity_date=normalized.activity_date,
                    period_start=normalized.period_start,
                    period_end=normalized.period_end,
                    supplier=normalized.supplier,
                    description=normalized.description,
                    activity_value=normalized.activity_value,
                    activity_unit=normalized.activity_unit,
                    normalized_value=normalized.normalized_value,
                    normalized_unit=normalized.normalized_unit,
                    co2e_kg=normalized.co2e_kg,
                    emission_factor_key=normalized.emission_factor_key,
                    quality_flags=normalized.quality_flags or [],
                    source_payload=normalized.source_payload or row,
                )

                AuditEvent.objects.create(
                    tenant=tenant,
                    normalized_activity=activity,
                    event_type=AuditEvent.CREATED,
                    actor="ingest_samples",
                    after={
                        "source_record_id": activity.source_record_id,
                        "source_type": activity.source_type,
                        "review_status": activity.review_status,
                        "quality_flags": activity.quality_flags,
                    },
                )

                raw.status = RawRecord.NORMALIZED
                raw.save(update_fields=["status"])
                normalized_count += 1

        run.succeeded_rows = normalized_count
        run.failed_rows = failed_count
        run.mark_complete()

        self.stdout.write(
            f"{source.source_type}: {source_file.name} -> "
            f"{normalized_count} normalized, {failed_count} failed"
        )

        return {"runs": 1, "raw": len(rows), "normalized": normalized_count, "failed": failed_count}

    def _read_rows(self, source_file):
        with source_file.open(newline="") as handle:
            return list(csv.DictReader(handle))

    def _normalize(self, tenant, source, row):
        if source.source_type == SourceConnection.SAP:
            return normalize_sap_row(tenant, row, sap_plant_map(tenant))
        if source.source_type == SourceConnection.UTILITY:
            return normalize_utility_row(tenant, row)
        if source.source_type == SourceConnection.TRAVEL:
            lookup_file = Path(settings.REPO_ROOT) / source.config["lookup_file"]
            if not lookup_file.exists():
                raise NormalizationError(f"Missing travel distance lookup file: {lookup_file}")
            return normalize_travel_row(tenant, row, distance_lookup(lookup_file))
        raise NormalizationError(f"Unsupported source type: {source.source_type}")

    def _source_row_id(self, source, row, index):
        fields = source.config.get("record_id_fields", [])
        values = [row.get(field, "").strip() for field in fields if row.get(field, "").strip()]
        return "-".join(values) if values else f"row-{index}"

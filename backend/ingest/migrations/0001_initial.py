# Generated manually for the assignment prototype foundation.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Tenant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Facility",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("facility_code", models.CharField(max_length=40)),
                ("name", models.CharField(max_length=160)),
                ("country", models.CharField(max_length=80)),
                ("region", models.CharField(blank=True, max_length=80)),
                ("egrid_subregion", models.CharField(blank=True, max_length=20)),
                ("utility_account", models.CharField(blank=True, max_length=80)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="facilities", to="ingest.tenant")),
            ],
            options={
                "ordering": ["facility_code"],
                "constraints": [
                    models.UniqueConstraint(fields=("tenant", "facility_code"), name="unique_facility_per_tenant"),
                ],
            },
        ),
        migrations.CreateModel(
            name="SourceConnection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_type", models.CharField(choices=[("sap", "SAP"), ("utility", "Utility"), ("travel", "Travel")], max_length=20)),
                ("name", models.CharField(max_length=160)),
                ("ingestion_mechanism", models.CharField(default="csv_upload", max_length=80)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="source_connections", to="ingest.tenant")),
            ],
            options={
                "ordering": ["source_type", "name"],
                "constraints": [
                    models.UniqueConstraint(fields=("tenant", "source_type", "name"), name="unique_source_per_tenant"),
                ],
            },
        ),
        migrations.CreateModel(
            name="IngestionRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("original_filename", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("complete", "Complete"), ("failed", "Failed")], default="pending", max_length=20)),
                ("total_rows", models.PositiveIntegerField(default=0)),
                ("succeeded_rows", models.PositiveIntegerField(default=0)),
                ("failed_rows", models.PositiveIntegerField(default=0)),
                ("notes", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("source_connection", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ingestion_runs", to="ingest.sourceconnection")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ingestion_runs", to="ingest.tenant")),
            ],
            options={"ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="RawRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_row_id", models.CharField(max_length=120)),
                ("payload", models.JSONField()),
                ("payload_hash", models.CharField(max_length=64)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("normalized", "Normalized"), ("failed", "Failed")], default="pending", max_length=20)),
                ("validation_errors", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("ingestion_run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="raw_records", to="ingest.ingestionrun")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="raw_records", to="ingest.tenant")),
            ],
            options={
                "ordering": ["id"],
                "indexes": [models.Index(fields=["tenant", "payload_hash"], name="ingest_rawr_tenant__c8d62b_idx")],
                "constraints": [
                    models.UniqueConstraint(fields=("ingestion_run", "source_row_id"), name="unique_raw_row_per_run"),
                ],
            },
        ),
        migrations.CreateModel(
            name="EmissionFactor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=80)),
                ("label", models.CharField(max_length=160)),
                ("factor_value", models.DecimalField(decimal_places=6, max_digits=14)),
                ("factor_unit", models.CharField(max_length=80)),
                ("source", models.CharField(max_length=255)),
                ("valid_from", models.DateField(blank=True, null=True)),
                ("valid_to", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="emission_factors", to="ingest.tenant")),
            ],
            options={
                "ordering": ["key"],
                "constraints": [
                    models.UniqueConstraint(fields=("tenant", "key", "factor_unit"), name="unique_factor_per_tenant"),
                ],
            },
        ),
        migrations.CreateModel(
            name="NormalizedActivity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_record_id", models.CharField(max_length=140)),
                ("source_type", models.CharField(max_length=20)),
                ("activity_category", models.CharField(max_length=80)),
                ("scope", models.CharField(choices=[("scope_1", "Scope 1"), ("scope_2", "Scope 2"), ("scope_3", "Scope 3")], max_length=20)),
                ("ghg_category", models.CharField(max_length=120)),
                ("activity_date", models.DateField(blank=True, null=True)),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("supplier", models.CharField(blank=True, max_length=160)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("activity_value", models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True)),
                ("activity_unit", models.CharField(blank=True, max_length=40)),
                ("normalized_value", models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True)),
                ("normalized_unit", models.CharField(blank=True, max_length=40)),
                ("co2e_kg", models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True)),
                ("emission_factor_key", models.CharField(blank=True, max_length=80)),
                ("quality_flags", models.JSONField(blank=True, default=list)),
                ("review_status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("locked", "Locked")], default="pending", max_length=20)),
                ("source_payload", models.JSONField(blank=True, default=dict)),
                ("edited_payload", models.JSONField(blank=True, default=dict)),
                ("approved_by", models.CharField(blank=True, max_length=120)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("locked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("facility", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="normalized_activities", to="ingest.facility")),
                ("ingestion_run", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="normalized_activities", to="ingest.ingestionrun")),
                ("raw_record", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="normalized_activity", to="ingest.rawrecord")),
                ("source_connection", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="normalized_activities", to="ingest.sourceconnection")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="normalized_activities", to="ingest.tenant")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant", "review_status"], name="ingest_norm_tenant__cc71b6_idx"),
                    models.Index(fields=["tenant", "scope"], name="ingest_norm_tenant__8b1b31_idx"),
                    models.Index(fields=["tenant", "source_type"], name="ingest_norm_tenant__576610_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("tenant", "source_connection", "source_record_id"), name="unique_activity_source_record"),
                ],
            },
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("created", "Created"), ("edited", "Edited"), ("approved", "Approved"), ("rejected", "Rejected"), ("locked", "Locked")], max_length=30)),
                ("actor", models.CharField(default="system", max_length=120)),
                ("before", models.JSONField(blank=True, default=dict)),
                ("after", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("normalized_activity", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="ingest.normalizedactivity")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="ingest.tenant")),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["tenant", "event_type"], name="ingest_audi_tenant__3cef61_idx"),
                    models.Index(fields=["normalized_activity", "created_at"], name="ingest_audi_normali_7eef71_idx"),
                ],
            },
        ),
    ]

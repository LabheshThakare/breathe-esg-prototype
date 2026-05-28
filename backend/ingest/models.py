from django.db import models
from django.utils import timezone


class Tenant(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Facility(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="facilities")
    facility_code = models.CharField(max_length=40)
    name = models.CharField(max_length=160)
    country = models.CharField(max_length=80)
    region = models.CharField(max_length=80, blank=True)
    egrid_subregion = models.CharField(max_length=20, blank=True)
    utility_account = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["facility_code"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "facility_code"], name="unique_facility_per_tenant"),
        ]

    def __str__(self):
        return f"{self.facility_code} - {self.name}"


class SourceConnection(models.Model):
    SAP = "sap"
    UTILITY = "utility"
    TRAVEL = "travel"
    SOURCE_TYPES = [
        (SAP, "SAP"),
        (UTILITY, "Utility"),
        (TRAVEL, "Travel"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="source_connections")
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    name = models.CharField(max_length=160)
    ingestion_mechanism = models.CharField(max_length=80, default="csv_upload")
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_type", "name"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "source_type", "name"], name="unique_source_per_tenant"),
        ]

    def __str__(self):
        return f"{self.name} ({self.source_type})"


class IngestionRun(models.Model):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (COMPLETE, "Complete"),
        (FAILED, "Failed"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="ingestion_runs")
    source_connection = models.ForeignKey(SourceConnection, on_delete=models.PROTECT, related_name="ingestion_runs")
    original_filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    total_rows = models.PositiveIntegerField(default=0)
    succeeded_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def mark_complete(self):
        self.status = self.COMPLETE
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "total_rows", "succeeded_rows", "failed_rows"])

    def mark_failed(self, notes):
        self.status = self.FAILED
        self.notes = notes
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "notes", "completed_at"])

    def __str__(self):
        return f"{self.source_connection} run {self.pk}"


class RawRecord(models.Model):
    PENDING = "pending"
    NORMALIZED = "normalized"
    FAILED = "failed"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (NORMALIZED, "Normalized"),
        (FAILED, "Failed"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="raw_records")
    ingestion_run = models.ForeignKey(IngestionRun, on_delete=models.CASCADE, related_name="raw_records")
    source_row_id = models.CharField(max_length=120)
    payload = models.JSONField()
    payload_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    validation_errors = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["tenant", "payload_hash"], name="ingest_rawr_tenant__c8d62b_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["ingestion_run", "source_row_id"], name="unique_raw_row_per_run"),
        ]

    def __str__(self):
        return f"{self.ingestion_run_id}:{self.source_row_id}"


class EmissionFactor(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="emission_factors", null=True, blank=True)
    key = models.CharField(max_length=80)
    label = models.CharField(max_length=160)
    factor_value = models.DecimalField(max_digits=14, decimal_places=6)
    factor_unit = models.CharField(max_length=80)
    source = models.CharField(max_length=255)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "key", "factor_unit"], name="unique_factor_per_tenant"),
        ]

    def __str__(self):
        return f"{self.key} ({self.factor_unit})"


class NormalizedActivity(models.Model):
    SCOPE_1 = "scope_1"
    SCOPE_2 = "scope_2"
    SCOPE_3 = "scope_3"
    SCOPE_CHOICES = [
        (SCOPE_1, "Scope 1"),
        (SCOPE_2, "Scope 2"),
        (SCOPE_3, "Scope 3"),
    ]

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    LOCKED = "locked"
    REVIEW_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (LOCKED, "Locked"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="normalized_activities")
    source_connection = models.ForeignKey(SourceConnection, on_delete=models.PROTECT, related_name="normalized_activities")
    ingestion_run = models.ForeignKey(IngestionRun, on_delete=models.PROTECT, related_name="normalized_activities")
    raw_record = models.OneToOneField(RawRecord, on_delete=models.PROTECT, related_name="normalized_activity")
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="normalized_activities", null=True, blank=True)
    source_record_id = models.CharField(max_length=140)
    source_type = models.CharField(max_length=20)
    activity_category = models.CharField(max_length=80)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    ghg_category = models.CharField(max_length=120)
    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    supplier = models.CharField(max_length=160, blank=True)
    description = models.CharField(max_length=255, blank=True)
    activity_value = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    activity_unit = models.CharField(max_length=40, blank=True)
    normalized_value = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    normalized_unit = models.CharField(max_length=40, blank=True)
    co2e_kg = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    emission_factor_key = models.CharField(max_length=80, blank=True)
    quality_flags = models.JSONField(default=list, blank=True)
    review_status = models.CharField(max_length=20, choices=REVIEW_CHOICES, default=PENDING)
    source_payload = models.JSONField(default=dict, blank=True)
    edited_payload = models.JSONField(default=dict, blank=True)
    approved_by = models.CharField(max_length=120, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "review_status"], name="ingest_norm_tenant__cc71b6_idx"),
            models.Index(fields=["tenant", "scope"], name="ingest_norm_tenant__8b1b31_idx"),
            models.Index(fields=["tenant", "source_type"], name="ingest_norm_tenant__576610_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "source_connection", "source_record_id"],
                name="unique_activity_source_record",
            ),
        ]

    def __str__(self):
        return f"{self.source_type}:{self.source_record_id}"


class AuditEvent(models.Model):
    CREATED = "created"
    EDITED = "edited"
    APPROVED = "approved"
    REJECTED = "rejected"
    LOCKED = "locked"
    EVENT_CHOICES = [
        (CREATED, "Created"),
        (EDITED, "Edited"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (LOCKED, "Locked"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="audit_events")
    normalized_activity = models.ForeignKey(NormalizedActivity, on_delete=models.CASCADE, related_name="audit_events")
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    actor = models.CharField(max_length=120, default="system")
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "event_type"], name="ingest_audi_tenant__3cef61_idx"),
            models.Index(fields=["normalized_activity", "created_at"], name="ingest_audi_normali_7eef71_idx"),
        ]

    def __str__(self):
        return f"{self.event_type} activity={self.normalized_activity_id}"

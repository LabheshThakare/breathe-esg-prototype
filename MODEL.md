# Data Model

## Design Goal

The model separates source truth from analyst-reviewed carbon activity. Raw rows are preserved exactly as received, normalized rows are derived from those raw rows, and every analyst action is recorded as an audit event. This lets the system answer three different questions:

- What did the client source system send us?
- What did Breathe ESG infer from it?
- Who reviewed or changed that inference before audit lock?

## Core Entities

### Tenant

Represents one client company. Every operational table carries `tenant_id` so data, source mappings, review queues, and audit records are isolated by customer.

Important fields:

- `id`
- `name`
- `slug`
- `created_at`

Why: multi-tenancy must be explicit, not inferred from filenames or users. Even in a prototype, all queries should filter by tenant.

### Facility

Maps client-specific operational codes to real reporting locations.

Important fields:

- `tenant_id`
- `facility_code`
- `name`
- `country`
- `region`
- `egrid_subregion`
- `utility_account`
- `metadata`

Why: SAP plant codes like `DE01` and utility account numbers like `AE-7750192` are not self-explanatory. Facility mapping is required before emissions can be grouped by site, country, or grid region.

### SourceConnection

Represents one configured source of incoming data.

Important fields:

- `tenant_id`
- `source_type`: `sap`, `utility`, `travel`
- `name`
- `ingestion_mechanism`: for this prototype, CSV upload
- `config`: JSON for source-specific mappings such as SAP plant lookup, airport distance lookup, or utility account mapping
- `created_at`

Why: a normalized activity should know which connection produced it. "SAP" alone is not enough; a tenant may have multiple SAP exports, travel platforms, or utility accounts.

### IngestionRun

Represents one import attempt.

Important fields:

- `tenant_id`
- `source_connection_id`
- `original_filename`
- `status`: `pending`, `complete`, `failed`
- `total_rows`
- `succeeded_rows`
- `failed_rows`
- `started_at`
- `completed_at`
- `notes`

Why: analysts need to see what came in and whether a file partially failed. Runs also support reprocessing and debugging without losing the original file context.

### RawRecord

Stores the exact source row before normalization.

Important fields:

- `tenant_id`
- `ingestion_run_id`
- `source_row_id`
- `payload`: full original row as JSON
- `payload_hash`
- `status`: `pending`, `normalized`, `failed`
- `validation_errors`
- `created_at`

Why: auditability depends on preserving original source data. Normalized fields may be corrected later, but the raw payload should remain immutable.

### NormalizedActivity

The common reviewable row produced from any source.

Important fields:

- `tenant_id`
- `source_connection_id`
- `ingestion_run_id`
- `raw_record_id`
- `facility_id`
- `source_record_id`
- `source_type`
- `activity_category`: examples: `fuel_combustion`, `purchased_electricity`, `business_travel`, `purchased_goods`
- `scope`: `scope_1`, `scope_2`, `scope_3`
- `ghg_category`: examples: `mobile_combustion`, `stationary_combustion`, `purchased_electricity_location_based`, `scope_3_category_1`, `scope_3_category_6`
- `activity_date`
- `period_start`
- `period_end`
- `supplier`
- `description`
- `activity_value`
- `activity_unit`
- `normalized_value`
- `normalized_unit`
- `co2e_kg`
- `emission_factor_key`
- `quality_flags`
- `review_status`: `pending`, `approved`, `rejected`, `locked`
- `source_payload`
- `edited_payload`
- `approved_by`
- `approved_at`
- `locked_at`
- `created_at`
- `updated_at`

Why: the analyst should review one consistent shape regardless of whether the row came from SAP, a utility portal, or travel expense data.

## Source Mapping

### SAP Fuel and Procurement

Source fixture: `sample_data/sap_fuel_procurement_export.csv`

Mapping:

- `WERKS` maps to `Facility.facility_code` through `sample_data/sap_plant_lookup.csv`.
- Fuel materials such as `DIESEL-B7`, `GASOLINE-UNL`, `LPG-KG`, and `NATGAS-KWH` become Scope 1.
- Purchased goods such as `STEEL-COIL`, `CORRUGATE-KG`, and `PALLET-WOOD` become Scope 3 Category 1.
- `MENGE` and `MEINS` become the source activity quantity and unit.
- Units normalize to canonical units such as `L`, `kWh`, `kg`, `metric_ton`, or `each`.
- `BWART` movement type helps flag reversals or credits.

Important flags:

- `unknown_plant`
- `ambiguous_unit`
- `negative_quantity`
- `unsupported_material`
- `date_parse_warning`

### Utility Electricity

Source fixture: `sample_data/utility_electricity_portal_export.csv`

Mapping:

- `facility_code` maps directly to `Facility`.
- `billing_period_start` and `billing_period_end` populate the activity period.
- `usage_quantity` and `usage_unit` normalize to `kWh`.
- Electricity rows become Scope 2.
- `tariff_code`, `rate_schedule`, `demand_kw`, and `total_bill_amount` remain in `source_payload` for review and future tariff analysis.

Important flags:

- `estimated_bill`
- `zero_usage`
- `unknown_facility`
- `non_calendar_billing_period`
- `missing_meter_number`

### Corporate Travel

Source fixture: `sample_data/corporate_travel_concur_like_export.csv`

Mapping:

- `expense_entry_id` is the source record id.
- `category` determines travel subcategory: flight, hotel, rail, ground transport.
- Flights use supplied distance when present, otherwise `origin` and `destination` are resolved through `sample_data/airport_distance_lookup.csv`.
- Hotels use `nights`, `rooms`, and employee region/country.
- Ground transport uses distance and vehicle/fuel fields where available.
- Travel rows become Scope 3 Category 6, business travel.

Important flags:

- `missing_distance`
- `invalid_airport_code`
- `pending_source_approval`
- `unsupported_travel_category`
- `missing_nights`

## Review and Locking

Rows start as `pending`. Analysts can:

- approve a row when the normalized values and flags are acceptable
- reject a row when it should not enter the inventory
- edit limited normalized fields before approval
- lock approved rows when they are ready for audit export

Locked rows should not be editable. If a locked row needs correction, the better production pattern is a reversal or superseding activity, not mutation in place.

## Audit Trail

`AuditEvent` records changes to review state and analyst edits.

Important fields:

- `tenant_id`
- `normalized_activity_id`
- `event_type`: `created`, `edited`, `approved`, `rejected`, `locked`
- `actor`
- `before`
- `after`
- `created_at`

Why: auditors need to understand not only the final number, but how it got there.

## Unit Normalization

The prototype normalizes source units into calculation units but preserves source units.

Examples:

- `GAL` to `L` for gasoline
- `KL` to `L` for diesel
- `TON` to `metric_ton` only when the tenant mapping confirms metric ton vs short ton
- `mi` to `km` for travel distance
- `kWh` remains `kWh`

Unit conversion should happen before emission factor application. If a source unit is ambiguous, the row should be flagged rather than silently converted.

## Emission Factors

The prototype should store emission factor metadata separately from activity rows:

- `key`
- `label`
- `factor_value`
- `factor_unit`
- `source`
- `valid_from`
- `valid_to`

`NormalizedActivity` stores the factor key used at calculation time. This keeps rows explainable even after factors are updated.

## Why This Model Is Smaller Than a Production Model

This prototype intentionally does not model every ERP dimension, utility tariff line item, or travel passenger segment. It models the layer Breathe ESG needs first: source tracking, normalization, review, and auditability.


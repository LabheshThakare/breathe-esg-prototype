# Decisions

## Product Scope

I built the assignment around a narrow ingestion and analyst-review workflow:

1. Upload source-specific CSV files.
2. Preserve every raw row.
3. Normalize rows into a shared activity model.
4. Flag rows that are missing mappings, ambiguous, or suspicious.
5. Let an analyst approve, reject, or lock rows for audit.

This is smaller than a full carbon platform, but it directly targets the assignment's highest-risk problem: messy enterprise data becoming defensible audit data.

## Decision 1: Use CSV Uploads for the Prototype

Choice: all three source types enter through CSV upload.

Why:

- The assignment gives four days, not enough time to build real SAP, utility, and travel integrations safely.
- CSV is still realistic. Enterprise onboarding often starts with exported files before API credentials, middleware, and security reviews are complete.
- CSV fixtures let reviewers inspect the exact edge cases the model handles.

What I would ask the PM:

- Do we expect this prototype to prove integration architecture or analyst workflow?
- Will the client provide API credentials during onboarding, or will the first milestone be file-based?
- How often will data arrive: monthly, weekly, daily, or ad hoc?

## Decision 2: SAP Slice Is Material Movement Export, Not Full SAP Integration

Choice: model SAP as a material movement/procurement export with IDoc/OData-like fields, not a live SAP connector.

Why:

- SAP S/4HANA exposes material document APIs, and SAP material records commonly include plant, movement type, material number, quantity, and base unit fields.
- Fuel consumption and procurement activity can both appear as material/procurement movements.
- A flat export is realistic for client onboarding because SAP access is often mediated by an internal SAP team or middleware.

Handled:

- Plant codes through lookup table
- Fuel and procurement materials
- Mixed units
- German-style date/header hints
- Reversal/credit movement rows

Ignored:

- Live OData authentication
- IDoc fixed-width parsing
- Batch, storage location, GL account, cost center, and purchase order approval state
- Material master enrichment beyond the sample material codes

What I would ask the PM:

- Which SAP module is the source of truth: MM, FI, PM, or a data warehouse extract?
- Are plant codes already mapped to ESG reporting facilities?
- Are we calculating from quantities, spend, or both?

## Decision 3: Utility Slice Is Portal Billing CSV Inspired by Green Button Data

Choice: model utility electricity as a portal CSV export of billing-period usage, not PDF bill parsing or full Green Button XML.

Why:

- Many facilities teams download portal CSVs or spreadsheet exports even when a utility has a richer standard.
- Green Button shows what a more standardized utility integration could contain: interval usage, billing summary, meters, and authorized data sharing.
- Billing-period rows are enough to test the carbon workflow: meters, kWh, demand, tariffs, non-calendar periods, and estimated bills.

Handled:

- `kWh` usage
- Meter number
- Utility account
- Demand in kW
- Tariff/rate schedule
- Billing periods that cross months
- Estimated and zero-usage bills

Ignored:

- PDF bill extraction
- Interval-level meter readings
- Green Button XML schema parsing
- Market-based electricity instruments and supplier-specific certificate matching

What I would ask the PM:

- Do analysts need monthly accruals split by calendar month?
- Are renewable energy certificates or supplier-specific factors in scope?
- Is the client comfortable granting utility portal access, or will facilities upload files?

## Decision 4: Travel Slice Is Expense/Booking Export, Not Full Travel API Pull

Choice: model travel as Concur/Navan-like expense rows with flight, hotel, rail, and ground transport categories.

Why:

- Travel platforms expose expense entries, configured expense types, workflow status, and travel-related records, but exact access depends on edition, scopes, and customer configuration.
- For emissions, category and activity details matter more than spend alone.
- Real travel data is incomplete: flight distance may be missing, hotels may be represented by nights, and ground transport may only have receipt distance.

Handled:

- Flight rows with airport codes and optional distance
- Airport distance lookup when distance is missing
- Hotel rows by nights and rooms
- Ground transport by distance, vehicle class, and fuel type
- Source approval status

Ignored:

- OAuth and API scopes
- Traveler PII beyond employee id/region
- Multi-passenger allocations
- Cabin class and radiative forcing uplift
- Receipt images and itinerary reconciliation

What I would ask the PM:

- Do we ingest approved expenses only, or all submitted travel for early estimates?
- Which travel platform does the client actually use?
- Are airport pair distance and cabin class available?

## Decision 5: Review Flags Are First-Class

Choice: suspicious conditions are stored as structured `quality_flags`, not only as error text.

Why:

- Analysts need filtering, not just logs.
- Some rows are not invalid, but still need human judgment. Example: estimated utility bill or ambiguous SAP unit.
- Structured flags can drive dashboard counts and audit explanations.

Examples:

- `unknown_plant`
- `estimated_bill`
- `non_calendar_billing_period`
- `missing_distance`
- `invalid_airport_code`
- `pending_source_approval`
- `negative_quantity`

## Decision 6: Preserve Raw Payloads

Choice: keep `RawRecord.payload` and copy relevant source fields into `NormalizedActivity.source_payload`.

Why:

- Source-of-truth tracking is explicitly required.
- Analysts and auditors need to compare the normalized activity to the original row.
- Reprocessing logic can change without losing what was originally received.

## Decision 7: Keep Authentication Simple in Prototype

Choice: document multi-tenancy in the model, but do not make auth the core demonstration.

Why:

- The assignment grades data model, decisions, source realism, UX, and tradeoffs.
- For a prototype, a seeded demo tenant and analyst role are enough to show the workflow.
- Production auth would require SSO, tenant membership, role-based access, and row-level authorization.

What I would ask the PM:

- Are analysts internal Breathe ESG users, client users, or both?
- Do clients need to log in and review their own rows?
- Should auditors get read-only access?


# Backend

Django REST backend for the Breathe ESG ingestion prototype.

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_foundation
python manage.py ingest_samples
python manage.py runserver
```

Health check:

```text
http://127.0.0.1:8000/api/health/
```

Review API:

```text
GET  /api/
GET  /api/dashboard/
GET  /api/activities/
GET  /api/activities/?source_type=sap
GET  /api/activities/?review_status=pending
GET  /api/activities/?flag=estimated_bill
GET  /api/activities/<id>/
POST /api/activities/<id>/approve/
POST /api/activities/<id>/reject/
POST /api/activities/<id>/lock/
GET  /api/failed-records/
GET  /api/runs/
```

POST actions accept an optional JSON body:

```json
{"actor": "Analyst Name"}
```

Foundation seed data:

- demo tenant: `demo-enterprise`
- facilities loaded from `../sample_data/sap_plant_lookup.csv`
- source connections for SAP, utility electricity, and corporate travel
- placeholder emission factors with explicit "replace before production" source text

Sample ingestion:

```bash
python manage.py ingest_samples
```

Expected local result:

```text
sap: sap_fuel_procurement_export.csv -> 9 normalized, 1 failed
travel: corporate_travel_concur_like_export.csv -> 10 normalized, 1 failed
utility: utility_electricity_portal_export.csv -> 6 normalized, 1 failed
Ingested samples: 3 runs, 28 raw rows, 25 normalized activities, 3 failed rows.
```

The command clears prior sample-ingestion output by default so it can be rerun during development. Use `--keep-existing` only if you intentionally want to keep prior runs.

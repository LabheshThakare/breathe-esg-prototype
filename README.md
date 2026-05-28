# Breathe ESG Ingestion Prototype

Prototype for ingesting messy enterprise activity data, normalizing it into reviewable emissions activity rows, and letting analysts approve or reject rows before audit lock.

## What It Handles

- SAP-style fuel and procurement CSV exports
- Utility portal electricity CSV exports
- Concur/Navan-like corporate travel CSV exports
- Raw source row preservation
- Normalized activity rows with Scope 1, Scope 2, and Scope 3 categories
- Quality flags for suspicious rows
- Failed-row visibility
- Analyst review actions: approve, reject, lock
- Audit events for ingestion and review actions

## Required Assignment Docs

- [MODEL.md](MODEL.md)
- [DECISIONS.md](DECISIONS.md)
- [TRADEOFFS.md](TRADEOFFS.md)
- [SOURCES.md](SOURCES.md)

## Local Setup

Backend:

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

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173/
```

If Vite chooses another port, use the URL it prints.

## API

```text
GET  /api/dashboard/
GET  /api/activities/
GET  /api/activities/<id>/
POST /api/activities/<id>/approve/
POST /api/activities/<id>/reject/
POST /api/activities/<id>/lock/
GET  /api/failed-records/
GET  /api/runs/
```

Useful filters:

```text
/api/activities/?source_type=sap
/api/activities/?scope=scope_2
/api/activities/?review_status=pending
/api/activities/?flag=estimated_bill
```

## Sample Data

Fixtures live in [sample_data](sample_data/):

- `sap_fuel_procurement_export.csv`
- `sap_plant_lookup.csv`
- `utility_electricity_portal_export.csv`
- `corporate_travel_concur_like_export.csv`
- `airport_distance_lookup.csv`

Expected ingestion result:

```text
3 ingestion runs
28 raw rows
25 normalized activities
3 failed rows
```

The failed rows are intentional edge cases: unknown SAP plant, unknown utility facility, and invalid travel airport pair.

## Deployment

This repo is configured for a single Render web service:

- `build.sh` installs Python and Node dependencies, builds React into Django static files, and runs `collectstatic`.
- `render.yaml` defines the web service and Postgres database.
- The start command runs migrations, seeds the demo foundation, ingests the sample rows, and starts Gunicorn.

Render start command:

```bash
cd backend && python manage.py migrate && python manage.py seed_foundation && python manage.py ingest_samples && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

Required environment variables:

```text
SECRET_KEY
DEBUG=False
DATABASE_URL
ALLOWED_HOSTS=.onrender.com,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
```

## Prototype Notes

The seeded emission factors are placeholders. They exist so the review workflow can show calculated CO2e, but production would need a governed, versioned factor library with source metadata and validity dates.


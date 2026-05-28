import csv
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ingest.models import EmissionFactor, Facility, SourceConnection, Tenant


class Command(BaseCommand):
    help = "Seed the demo tenant, facilities, source connections, and placeholder emission factors."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-slug", default="demo-enterprise")
        parser.add_argument("--tenant-name", default="Demo Enterprise Client")

    def handle(self, *args, **options):
        sample_dir = Path(settings.REPO_ROOT) / "sample_data"
        plant_lookup_path = sample_dir / "sap_plant_lookup.csv"
        utility_path = sample_dir / "utility_electricity_portal_export.csv"

        if not plant_lookup_path.exists():
            raise CommandError(f"Missing fixture: {plant_lookup_path}")

        tenant, _created = Tenant.objects.update_or_create(
            slug=options["tenant_slug"],
            defaults={"name": options["tenant_name"]},
        )

        utility_accounts = self._load_utility_accounts(utility_path)
        facility_count = self._seed_facilities(tenant, plant_lookup_path, utility_accounts)
        source_count = self._seed_sources(tenant)
        factor_count = self._seed_placeholder_factors(tenant)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {tenant.slug}: {facility_count} facilities, "
                f"{source_count} source connections, {factor_count} emission factors."
            )
        )

    def _load_utility_accounts(self, utility_path):
        if not utility_path.exists():
            return {}

        accounts = {}
        with utility_path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                facility_code = row.get("facility_code", "").strip()
                account_number = row.get("account_number", "").strip()
                if facility_code and account_number and facility_code not in accounts:
                    accounts[facility_code] = account_number
        return accounts

    def _seed_facilities(self, tenant, plant_lookup_path, utility_accounts):
        count = 0
        with plant_lookup_path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                facility_code = row["facility_code"].strip()
                Facility.objects.update_or_create(
                    tenant=tenant,
                    facility_code=facility_code,
                    defaults={
                        "name": row["plant_name"].strip(),
                        "country": row["country"].strip(),
                        "region": row["region"].strip(),
                        "utility_account": utility_accounts.get(facility_code, ""),
                        "metadata": {
                            "sap_client": row["mandt"].strip(),
                            "sap_plant": row["werks"].strip(),
                            "notes": row.get("notes", "").strip(),
                        },
                    },
                )
                count += 1
        return count

    def _seed_sources(self, tenant):
        sources = [
            {
                "source_type": SourceConnection.SAP,
                "name": "SAP material movements CSV",
                "config": {
                    "source_file": "sample_data/sap_fuel_procurement_export.csv",
                    "lookup_file": "sample_data/sap_plant_lookup.csv",
                    "record_id_fields": ["IDOCNUM", "EBELN", "EBELP"],
                },
            },
            {
                "source_type": SourceConnection.UTILITY,
                "name": "Utility portal electricity CSV",
                "config": {
                    "source_file": "sample_data/utility_electricity_portal_export.csv",
                    "record_id_fields": ["utility_name", "account_number", "meter_number", "bill_number"],
                },
            },
            {
                "source_type": SourceConnection.TRAVEL,
                "name": "Corporate travel expense CSV",
                "config": {
                    "source_file": "sample_data/corporate_travel_concur_like_export.csv",
                    "lookup_file": "sample_data/airport_distance_lookup.csv",
                    "record_id_fields": ["report_id", "expense_entry_id"],
                },
            },
        ]

        for source in sources:
            SourceConnection.objects.update_or_create(
                tenant=tenant,
                source_type=source["source_type"],
                name=source["name"],
                defaults={
                    "ingestion_mechanism": "csv_upload",
                    "config": source["config"],
                },
            )
        return len(sources)

    def _seed_placeholder_factors(self, tenant):
        factors = [
            ("diesel_l", "Diesel combustion", "kg_co2e_per_l", "Assignment placeholder; replace with official factor set", "2.680000"),
            ("gasoline_l", "Gasoline combustion", "kg_co2e_per_l", "Assignment placeholder; replace with official factor set", "2.310000"),
            ("natural_gas_kwh", "Natural gas combustion", "kg_co2e_per_kwh", "Assignment placeholder; replace with official factor set", "0.182000"),
            ("lpg_kg", "LPG combustion", "kg_co2e_per_kg", "Assignment placeholder; replace with official factor set", "3.000000"),
            ("electricity_kwh", "Grid electricity", "kg_co2e_per_kwh", "Assignment placeholder; replace with region-specific grid factor", "0.400000"),
            ("steel_metric_ton", "Purchased steel", "kg_co2e_per_metric_ton", "Assignment placeholder; replace with supplier/product factor", "1900.000000"),
            ("corrugated_kg", "Corrugated packaging", "kg_co2e_per_kg", "Assignment placeholder; replace with supplier/product factor", "0.700000"),
            ("pallet_each", "Wood pallet", "kg_co2e_per_each", "Assignment placeholder; replace with supplier/product factor", "25.000000"),
            ("air_travel_km", "Business air travel", "kg_co2e_per_passenger_km", "Assignment placeholder; replace with travel factor set", "0.150000"),
            ("rail_km", "Business rail travel", "kg_co2e_per_passenger_km", "Assignment placeholder; replace with travel factor set", "0.035000"),
            ("ground_gasoline_km", "Ground transport gasoline vehicle", "kg_co2e_per_vehicle_km", "Assignment placeholder; replace with vehicle-class factor", "0.250000"),
            ("hotel_room_night", "Hotel stay", "kg_co2e_per_room_night", "Assignment placeholder; replace with country-specific hotel factor", "15.000000"),
        ]

        for key, label, unit, source, value in factors:
            EmissionFactor.objects.update_or_create(
                tenant=tenant,
                key=key,
                factor_unit=unit,
                defaults={
                    "label": label,
                    "factor_value": Decimal(value),
                    "source": source,
                },
            )
        return len(factors)

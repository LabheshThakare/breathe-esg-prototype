import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ingest.models import EmissionFactor, Facility, NormalizedActivity, SourceConnection


GALLON_TO_LITER = Decimal("3.78541")
KILOLITER_TO_LITER = Decimal("1000")
MILE_TO_KM = Decimal("1.60934")


class NormalizationError(ValueError):
    pass


@dataclass
class NormalizedResult:
    source_record_id: str
    source_type: str
    activity_category: str
    scope: str
    ghg_category: str
    facility: Facility | None = None
    activity_date: object = None
    period_start: object = None
    period_end: object = None
    supplier: str = ""
    description: str = ""
    activity_value: Decimal | None = None
    activity_unit: str = ""
    normalized_value: Decimal | None = None
    normalized_unit: str = ""
    co2e_kg: Decimal | None = None
    emission_factor_key: str = ""
    quality_flags: list[str] | None = None
    source_payload: dict | None = None


def row_hash(row):
    encoded = json.dumps(row, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_csv(path):
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def parse_decimal(value, field_name):
    cleaned = (value or "").strip().replace(",", "")
    if cleaned == "":
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise NormalizationError(f"{field_name} is not a number: {value}") from exc


def parse_date(value, field_name):
    cleaned = (value or "").strip()
    if not cleaned:
        return None

    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%d-%b-%Y",
    ]
    for date_format in formats:
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            pass
    raise NormalizationError(f"{field_name} has unsupported date format: {value}")


def factor_value(tenant, key):
    factor = EmissionFactor.objects.filter(tenant=tenant, key=key).first()
    if not factor:
        raise NormalizationError(f"Missing emission factor: {key}")
    return factor.factor_value


def kg_co2e(tenant, key, value):
    if value is None:
        return None
    return (value * factor_value(tenant, key)).quantize(Decimal("0.001"))


def facility_by_code(tenant, facility_code):
    return Facility.objects.filter(tenant=tenant, facility_code=facility_code).first()


def sap_plant_map(tenant):
    mapping = {}
    for facility in Facility.objects.filter(tenant=tenant):
        sap_plant = facility.metadata.get("sap_plant")
        if sap_plant:
            mapping[sap_plant] = facility
    return mapping


def distance_lookup(path):
    lookup = {}
    for row in read_csv(path):
        lookup[(row["origin"].strip().upper(), row["destination"].strip().upper())] = parse_decimal(
            row["distance_km"], "distance_km"
        )
    return lookup


def normalize_sap_row(tenant, row, plant_lookup):
    flags = []
    material = row["MATNR"].strip().upper()
    unit = row["MEINS"].strip()
    quantity = parse_decimal(row["MENGE"], "MENGE")
    activity_date = parse_date(row["BUDAT"], "BUDAT")
    facility = plant_lookup.get(row["WERKS"].strip())

    if not facility:
        raise NormalizationError(f"Unknown SAP plant code: {row['WERKS']}")
    if quantity is None:
        raise NormalizationError("MENGE is required")

    if quantity < 0:
        flags.append("reversal_or_credit")

    normalized_value = quantity
    normalized_unit = unit
    scope = NormalizedActivity.SCOPE_1
    ghg_category = "mobile_combustion"
    activity_category = "fuel_combustion"
    factor_key = ""

    if material == "DIESEL-B7":
        factor_key = "diesel_l"
        if unit.upper() == "KL":
            normalized_value = quantity * KILOLITER_TO_LITER
            normalized_unit = "L"
        elif unit.upper() != "L":
            raise NormalizationError(f"Unsupported diesel unit: {unit}")
    elif material == "GASOLINE-UNL":
        factor_key = "gasoline_l"
        if unit.upper() == "GAL":
            normalized_value = quantity * GALLON_TO_LITER
            normalized_unit = "L"
        elif unit.upper() != "L":
            raise NormalizationError(f"Unsupported gasoline unit: {unit}")
    elif material == "NATGAS-KWH":
        factor_key = "natural_gas_kwh"
        ghg_category = "stationary_combustion"
        if unit.lower() != "kwh":
            raise NormalizationError(f"Unsupported natural gas unit: {unit}")
        normalized_unit = "kWh"
    elif material == "LPG-KG":
        factor_key = "lpg_kg"
        if unit.upper() != "KG":
            raise NormalizationError(f"Unsupported LPG unit: {unit}")
        normalized_unit = "kg"
    elif material == "STEEL-COIL":
        factor_key = "steel_metric_ton"
        scope = NormalizedActivity.SCOPE_3
        ghg_category = "scope_3_category_1_purchased_goods"
        activity_category = "purchased_goods"
        if unit.upper() == "TON":
            flags.append("ambiguous_unit_ton")
            normalized_unit = "metric_ton"
        else:
            raise NormalizationError(f"Unsupported steel unit: {unit}")
    elif material == "CORRUGATE-KG":
        factor_key = "corrugated_kg"
        scope = NormalizedActivity.SCOPE_3
        ghg_category = "scope_3_category_1_purchased_goods"
        activity_category = "purchased_goods"
        if unit.upper() != "KG":
            raise NormalizationError(f"Unsupported corrugate unit: {unit}")
        normalized_unit = "kg"
    elif material == "PALLET-WOOD":
        factor_key = "pallet_each"
        scope = NormalizedActivity.SCOPE_3
        ghg_category = "scope_3_category_1_purchased_goods"
        activity_category = "purchased_goods"
        if unit.upper() != "EA":
            raise NormalizationError(f"Unsupported pallet unit: {unit}")
        normalized_unit = "each"
    else:
        raise NormalizationError(f"Unsupported SAP material: {material}")

    return NormalizedResult(
        source_record_id="-".join([row["IDOCNUM"].strip(), row["EBELN"].strip(), row["EBELP"].strip()]),
        source_type=SourceConnection.SAP,
        activity_category=activity_category,
        scope=scope,
        ghg_category=ghg_category,
        facility=facility,
        activity_date=activity_date,
        supplier=row.get("NAME1", "").strip(),
        description=row.get("MAKTX", "").strip(),
        activity_value=quantity,
        activity_unit=unit,
        normalized_value=normalized_value,
        normalized_unit=normalized_unit,
        co2e_kg=kg_co2e(tenant, factor_key, normalized_value),
        emission_factor_key=factor_key,
        quality_flags=flags,
        source_payload=row,
    )


def normalize_utility_row(tenant, row):
    flags = []
    facility = facility_by_code(tenant, row.get("facility_code", "").strip())
    if not facility:
        raise NormalizationError(f"Unknown utility facility code: {row.get('facility_code')}")

    usage = parse_decimal(row["usage_quantity"], "usage_quantity")
    if usage is None:
        raise NormalizationError("usage_quantity is required")
    unit = row["usage_unit"].strip()
    if unit.lower() != "kwh":
        raise NormalizationError(f"Unsupported utility unit: {unit}")

    period_start = parse_date(row["billing_period_start"], "billing_period_start")
    period_end = parse_date(row["billing_period_end"], "billing_period_end")
    if period_start and period_end and not (period_start.day == 1 and period_end.day in [28, 29, 30, 31]):
        flags.append("non_calendar_billing_period")
    if row.get("estimated_bill", "").strip().lower() == "true" or row.get("read_type", "").strip().lower() == "estimated":
        flags.append("estimated_bill")
    if usage == 0:
        flags.append("zero_usage")

    return NormalizedResult(
        source_record_id="-".join(
            [
                row["utility_name"].strip(),
                row["account_number"].strip(),
                row["meter_number"].strip(),
                row["bill_number"].strip(),
            ]
        ),
        source_type=SourceConnection.UTILITY,
        activity_category="purchased_electricity",
        scope=NormalizedActivity.SCOPE_2,
        ghg_category="purchased_electricity_location_based",
        facility=facility,
        period_start=period_start,
        period_end=period_end,
        supplier=row["utility_name"].strip(),
        description=f"Electricity bill {row['bill_number'].strip()} / meter {row['meter_number'].strip()}",
        activity_value=usage,
        activity_unit=unit,
        normalized_value=usage,
        normalized_unit="kWh",
        co2e_kg=kg_co2e(tenant, "electricity_kwh", usage),
        emission_factor_key="electricity_kwh",
        quality_flags=flags,
        source_payload=row,
    )


def normalize_travel_row(tenant, row, distances):
    flags = []
    category = row["category"].strip().lower()
    transaction_date = parse_date(row["transaction_date"], "transaction_date")
    approval_status = row.get("approval_status", "").strip().lower()
    if approval_status != "approved":
        flags.append("pending_source_approval")

    if category == "flight":
        distance = parse_decimal(row.get("distance_value"), "distance_value")
        unit = row.get("distance_unit", "").strip()
        if distance is None:
            origin = row.get("origin", "").strip().upper()
            destination = row.get("destination", "").strip().upper()
            distance = distances.get((origin, destination))
            unit = "km"
            if distance is None:
                raise NormalizationError(f"Missing flight distance and unknown airport pair: {origin}-{destination}")
            flags.append("distance_derived_from_airport_lookup")
        normalized_distance = distance * MILE_TO_KM if unit.lower() == "mi" else distance
        if unit.lower() not in ["mi", "km"]:
            raise NormalizationError(f"Unsupported flight distance unit: {unit}")
        factor_key = "air_travel_km"
        activity_category = "business_travel_flight"
        description = f"Flight {row.get('origin', '').strip()}-{row.get('destination', '').strip()}"
    elif category == "rail":
        distance = parse_decimal(row.get("distance_value"), "distance_value")
        unit = row.get("distance_unit", "").strip()
        if distance is None:
            raise NormalizationError("Rail distance is required")
        normalized_distance = distance * MILE_TO_KM if unit.lower() == "mi" else distance
        if unit.lower() not in ["mi", "km"]:
            raise NormalizationError(f"Unsupported rail distance unit: {unit}")
        factor_key = "rail_km"
        activity_category = "business_travel_rail"
        description = f"Rail {row.get('origin', '').strip()}-{row.get('destination', '').strip()}"
    elif category == "ground transport":
        distance = parse_decimal(row.get("distance_value"), "distance_value")
        unit = row.get("distance_unit", "").strip()
        if distance is None:
            raise NormalizationError("Ground transport distance is required")
        normalized_distance = distance * MILE_TO_KM if unit.lower() == "mi" else distance
        if unit.lower() not in ["mi", "km"]:
            raise NormalizationError(f"Unsupported ground transport distance unit: {unit}")
        factor_key = "ground_gasoline_km"
        activity_category = "business_travel_ground_transport"
        description = f"{row.get('vendor', '').strip()} {row.get('vehicle_class', '').strip()} ground transport".strip()
    elif category == "hotel":
        nights = parse_decimal(row.get("nights"), "nights")
        rooms = parse_decimal(row.get("rooms"), "rooms") or Decimal("1")
        if nights is None:
            raise NormalizationError("Hotel nights are required")
        normalized_distance = nights * rooms
        factor_key = "hotel_room_night"
        activity_category = "business_travel_hotel"
        description = f"{row.get('vendor', '').strip()} hotel stay"
    else:
        raise NormalizationError(f"Unsupported travel category: {row['category']}")

    normalized_unit = "room_night" if category == "hotel" else "km"

    return NormalizedResult(
        source_record_id="-".join([row["report_id"].strip(), row["expense_entry_id"].strip()]),
        source_type=SourceConnection.TRAVEL,
        activity_category=activity_category,
        scope=NormalizedActivity.SCOPE_3,
        ghg_category="scope_3_category_6_business_travel",
        activity_date=transaction_date,
        supplier=row.get("vendor", "").strip(),
        description=description,
        activity_value=parse_decimal(row.get("distance_value") or row.get("nights"), "activity_value"),
        activity_unit=row.get("distance_unit", "").strip() or ("night" if category == "hotel" else ""),
        normalized_value=normalized_distance,
        normalized_unit=normalized_unit,
        co2e_kg=kg_co2e(tenant, factor_key, normalized_distance),
        emission_factor_key=factor_key,
        quality_flags=flags,
        source_payload=row,
    )

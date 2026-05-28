# Sample Data

These fixtures are intentionally realistic enough to exercise the assignment logic without pretending to be complete production integrations.

- `sap_fuel_procurement_export.csv`: SAP-style material movement export for fuel and purchased goods. It includes German-ish headers, mixed date formats, mixed units, plant codes, movement types, an unknown plant, and a reversal row.
- `sap_plant_lookup.csv`: Lookup table needed to map opaque SAP `WERKS` plant codes to facilities.
- `utility_electricity_portal_export.csv`: Portal CSV export for electricity bills. Billing periods do not always align to calendar months, bills include demand and tariff fields, and one bill is estimated.
- `corporate_travel_concur_like_export.csv`: Concur/Navan-like travel expense export covering flights, hotel nights, rail, ride hail, and rental car rows. Some flights require airport-distance lookup.
- `airport_distance_lookup.csv`: Small lookup used when travel rows provide airport codes but no distance.

The rows include a few deliberate review cases: unknown facility/plant codes, zero usage, estimated utility bills, pending travel approval, missing flight distance, invalid airport code, ambiguous procurement units, and credit/reversal quantities.

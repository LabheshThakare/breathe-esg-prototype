# Sources and Sample Data Rationale

## Summary

The sample data is fabricated, but each file is based on a realistic enterprise source shape. I deliberately included rows that should not pass cleanly, because real client onboarding data rarely arrives clean.

## 1. SAP Fuel and Procurement

Sample files:

- `sample_data/sap_fuel_procurement_export.csv`
- `sample_data/sap_plant_lookup.csv`

Researched shape:

- SAP material document and inventory APIs include material-document style concepts such as plant, material, quantity, unit, and movement type.
- SAP IDoc structures and exports often use technical field names and segment-oriented layouts.
- SAP environments can be localized, which is why the sample includes German-style date/header hints.

References:

- SAP Help Portal, Inventory OData services: https://help.sap.com/docs/SAP_S4HANA_CLOUD/3f57e7df4a114edabffe8b2d581a59ed/013f0f9ef9dc48daa3c4709ab8860333.html
- SAP Help Portal, IDoc structures overview: https://help.sap.com/docs/SAP_ERP/98c2704cf26a4120ae7168868b2e7da5/58cbc353b677b44ce10000000a174cb4.html
- SAP material document field reference for `WERKS`, `BWART`, `MATNR`, and `MENGE`: https://www.summit-bi.com/resources/sap-reference/tables/MATDOC

What the sample contains:

- `WERKS` plant codes like `DE01`, `US10`, `IN03`, and `GB20`
- A separate plant lookup because SAP plant codes are not meaningful to analysts
- Material codes for diesel, gasoline, natural gas, LPG, steel, corrugate, and pallets
- Movement types like `101`, `201`, and `202`
- Mixed quantity units: `L`, `kWh`, `GAL`, `TON`, `KG`, `KL`, `EA`
- Mixed date formats: ISO, US slash date, German dot date, and text month
- Local currencies: EUR, USD, INR, GBP

Why it looks this way:

- Fuel rows test Scope 1 normalization.
- Procurement rows test Scope 3 purchased goods categorization.
- Plant lookup tests source-code mapping.
- Unit variation tests whether the app preserves source values while normalizing calculation units.
- The unknown plant `ZZ99` should fail or be flagged.
- The negative gasoline row should be treated as a reversal/credit, not blindly counted as normal consumption.

What would break in a real deployment:

- The client may export from SAP BW, Datasphere, ECC, S/4HANA OData, IDoc, or a custom ABAP report with different columns.
- `TON` may mean metric ton, short ton, or a purchasing unit configured by the client.
- Material codes and movement types require tenant-specific mapping.
- Procurement emissions usually require supplier, product category, or spend-based factors that are not in this prototype.

## 2. Utility Electricity

Sample file:

- `sample_data/utility_electricity_portal_export.csv`

Researched shape:

- Utility data may be available through Green Button Download My Data, Green Button Connect My Data, portal CSVs, Excel exports, APIs, or PDFs.
- Green Button is based on the ESPI standard and can include interval usage, meters, billing summaries, costs, demand, and customer authorization flows.
- For this prototype, I chose a portal CSV that borrows the important reporting concepts without implementing Green Button XML.

References:

- U.S. Department of Energy, Green Button overview: https://www.energy.gov/node/369883
- Green Button Alliance, Connect My Data: https://www.greenbuttonalliance.org/green-button-connect-my-data-cmd
- Green Button Alliance, Usage Summary and interval function blocks: https://www.greenbuttonalliance.org/cmd-function-blocks
- Green Button Alliance, interval metering function block: https://www.greenbuttonalliance.org/fb04

What the sample contains:

- Utility name
- Account number
- Meter number
- Facility code
- Service address
- Bill number
- Billing period start/end
- Read type
- kWh usage
- Demand in kW
- Tariff code and rate schedule
- Total bill amount and currency
- Renewable energy percentage
- Estimated bill flag

Why it looks this way:

- Electricity emissions are Scope 2 and are usually driven by consumption in kWh.
- Utility billing periods often cross month boundaries, so the sample includes periods like `2025-12-18` to `2026-01-20`.
- Demand and tariff fields do not directly calculate emissions, but analysts often need them to reconcile bills.
- Estimated bills should be reviewable and possibly reversed or replaced later.
- Zero usage should be flagged because it may indicate a closed meter, missing data, or a true inactive period.

What would break in a real deployment:

- Green Button XML parsing is not implemented.
- PDF bills are not parsed.
- Interval data is not modeled.
- Market-based electricity accounting, renewable energy certificates, and supplier-specific factors are out of scope.
- Calendar-month allocation is flagged but not calculated.

## 3. Corporate Travel

Sample files:

- `sample_data/corporate_travel_concur_like_export.csv`
- `sample_data/airport_distance_lookup.csv`

Researched shape:

- SAP Concur exposes expense and travel-related APIs, but API access depends on product edition, scopes, and customer configuration.
- Expense configuration includes expense types and spend categories.
- Expense report workflows include approval status.
- Travel emissions need category-specific activity data, not only spend.

References:

- SAP Concur Help Portal: https://help.sap.com/docs/SAP_CONCUR
- SAP Concur Expense Configuration API: https://preview.developer.concur.com/api-reference/expense/expense-config/v4.expense.config.html
- SAP Concur expense workflow action documentation: https://preview.developer.concur.com/api-reference/expense/expense-report/post-report-workflow-action.html
- SAP Concur expense entry association documentation, showing entry-level API concepts: https://preview.developer.concur.com/api-reference/expense/expense-report/v3.expense-entry-attendee.html

What the sample contains:

- Report and expense entry ids
- Employee id and region
- Booking platform
- Transaction date and trip dates
- Travel category: flight, hotel, rail, ground transport
- Vendor
- Origin and destination codes
- Optional distance and distance unit
- Hotel nights and rooms
- Vehicle class and fuel type
- Amount and currency
- Source approval status

Why it looks this way:

- Flights may have airport codes but no distance, so the prototype needs an airport-distance lookup.
- Hotels are better represented by nights and rooms than by spend alone.
- Ground transport may include distance from receipt or app data.
- Pending source approval should block or flag analyst approval because the expense may still change.
- Invalid airport code `XXX` tests validation.

What would break in a real deployment:

- Airport distance lookup would need a complete airport database or geocoder.
- Cabin class, haul class, radiative forcing uplift, and multi-passenger allocation are not represented.
- Travel APIs may return itinerary, booking, card, and expense data separately.
- Travel categories and custom fields vary by client configuration.
- Employee PII and access control would need stricter handling.

## GHG Accounting References

These references guided the Scope mapping:

- GHG Protocol Scope 2 Guidance overview: https://ghgprotocol.org/scope-2-guidance
- GHG Protocol Corporate Standard FAQ: https://ghgprotocol.org/corporate-standard-frequently-asked-questions
- GHG Protocol Scope 3 FAQ: https://ghgprotocol.org/scope-3-frequently-asked-questions-0
- U.S. EPA Scopes 1, 2, and 3 emissions inventorying guidance: https://www.epa.gov/climateleadership/scopes-1-2-and-3-emissions-inventorying-and-guidance

Scope mapping used:

- Scope 1: company fuel combustion from SAP fuel rows
- Scope 2: purchased electricity from utility rows
- Scope 3 Category 1: purchased goods from SAP procurement rows
- Scope 3 Category 6: business travel from travel rows


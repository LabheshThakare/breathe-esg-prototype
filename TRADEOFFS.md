# Tradeoffs

## 1. I Did Not Build Live Source Integrations

I chose CSV upload instead of live SAP OData/IDoc ingestion, utility APIs, or Concur/Navan API pulls.

Why:

- Live integrations would consume most of the prototype time in authentication, credentials, tenant-specific setup, and vendor sandbox differences.
- The assignment's core risk is not whether an API call can be made. The core risk is whether messy rows can be normalized, reviewed, and defended.
- CSV files make the demo deterministic and easy to inspect.

What production would need:

- SAP connector or middleware integration
- Utility API/Green Button CMD support where available
- Travel platform OAuth, scopes, rate limits, and webhook or scheduled pulls
- Per-tenant connection health monitoring

## 2. I Did Not Build Full Emissions Factor Management

I would include simple factor keys and calculated `co2e_kg`, but not a full factor library.

Why:

- Correct factors vary by geography, reporting year, fuel type, method, market/location basis, and sometimes supplier contract.
- A weak generic factor library would create false confidence.
- The prototype should show where factors attach and how their source is tracked, not pretend to solve factor governance.

What production would need:

- Versioned factor library
- Factor source metadata
- Location-based and market-based Scope 2 methods
- Validity dates
- Tenant overrides
- Recalculation controls when factors are updated

## 3. I Did Not Build Calendar-Month Accrual Splitting

Utility bills often span two calendar months. I flag non-calendar billing periods but do not split them into monthly accruals.

Why:

- Splitting requires a policy decision: daily proration, interval data, weather-adjusted allocation, or financial close rules.
- A silent split could be less defensible than surfacing the original billing period.
- The analyst dashboard can approve the source bill as-is while documenting that reporting-period allocation is a future layer.

What production would need:

- Tenant reporting calendar
- Daily or interval allocation support
- Month-end accrual workflow
- Reversal logic when actual bills replace estimates

## 4. I Did Not Build PDF Bill Parsing

I chose utility portal CSV export over PDF bill extraction.

Why:

- PDF bills vary heavily by utility, tariff, jurisdiction, and layout.
- OCR and PDF table extraction can work, but they need confidence scoring and manual correction UI.
- The CSV path is more likely to produce a reliable prototype in four days.

What production would need:

- PDF parser per utility template or document AI extraction
- Confidence scores per extracted field
- Human correction workflow
- Bill image retention for audit support

## 5. I Did Not Build Advanced Travel Estimation

The sample travel data handles distance, hotel nights, and basic ground transport, but skips cabin class, radiative forcing, aircraft type, passenger allocation, and hotel country-specific factor nuance.

Why:

- Travel emissions can become a full product area.
- For the prototype, the important workflow is identifying whether activity data is sufficient and flagging what is missing.
- Airport-code distance lookup is enough to show the normalization problem without overfitting the sample.

What production would need:

- Airport database
- Great-circle distance calculation
- Cabin class and haul classification
- Country-specific hotel factors
- Rental car fuel economy assumptions
- Multi-passenger allocation


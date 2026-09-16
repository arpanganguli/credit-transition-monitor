# Private Credit Early-Warning & Loss Monitor

Upload a loan book, see which borrowers are deteriorating, understand exactly
why, and stress-test the portfolio's expected loss — without a black-box
model. Built to the 8-Week Build Plan for a private-credit / private-equity
audience: a credit analyst in software.

> **A user should be able to reproduce every calculation.** Every number this
> app shows traces back to a documented formula in `credit/`, backed by a
> pytest suite. There is no trained ML model in this build.

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate     # optional but recommended
pip install -r requirements.txt

# (Re)generate the 50-borrower synthetic demo portfolio (already included,
# but this is how it was produced and how to regenerate it)
python3 sample_data/generate_demo_data.py

# Run the test suite
pytest

# Launch the app
streamlit run app/streamlit_app.py
```

Open the app, click **Load demo portfolio** in the sidebar, and explore the
four screens: **Portfolio**, **Borrower**, **Risk Drivers**, **Stress Test**.

To use your own loan book instead, upload a CSV/Excel file via the sidebar.
Download the in-app template for the expected columns. Minimum required
columns: `borrower_id, ead, baseline_pd, baseline_lgd, revenue, ebitda, debt,
cash, interest_expense` (a `period` column enables period-on-period trend,
scoring and attribution — without it every borrower is treated as a single
snapshot).

## What this is (and isn't)

This is a **prototype for a paid design-partner pilot**, not a production
credit-risk system. Per the build plan:

- The early-warning scorecard is an **explainable rules engine**, not a
  trained model. Every point is traceable to one condition on one metric.
- The PD/LGD overlays are **hazard-rate and coverage-based heuristics**, not
  validated regulatory models (IRB, CECL, IFRS 9 ECL, etc.).
- Risk-band thresholds, overlay multipliers, and pilot pricing are **product
  assumptions to test with users**, not statistically calibrated
  probabilities, market-standard pricing, or investment advice.
- Satellite imagery, an LLM chatbot, sophisticated ML, multi-factor Monte
  Carlo simulation, a React frontend, multi-tenancy, automated underwriting,
  portfolio optimisation and ESG scoring are all deliberately **out of
  scope** for this build (see "Deliberately out of scope" below).

## Architecture

```
CSV / Excel upload
      |
Validation (pydantic) -- data/validation.py
      |
Normalised data (SQLite) -- database/schema.py, database/db.py
      |------------------------------|
Companies House enrichment      Customer financial history
(data/companies_house.py)              |
      |------------- Financial ratios -+ (credit/ratios.py)
                        |
                Early-warning engine (credit/early_warning.py)
                   |            |
             PD overlay     LGD overlay
        (credit/pd_overlay) (credit/lgd_overlay)
                   |            |
                   +-- Expected Loss --+  (credit/expected_loss.py)
                            |
                  EL attribution (credit/attribution.py)
                            |
                     Stress testing (credit/scenarios.py)
                            |
                       Streamlit UI (app/)
```

Plain **Python + Pandas + SQLite + Streamlit + Pytest** — no React, no
Kubernetes, no separate API layer, no ORM. Every calculation module in
`credit/` is pure (no I/O, no Streamlit calls, no hidden state), which is
what makes it unit-testable and reproducible.

### Repository layout

```
credit-monitor/
  app/                Streamlit UI
    streamlit_app.py    Home: branding, data load, executive summary
    pages/
      1_Portfolio.py     Screen 1: sortable portfolio ranking
      2_Borrower.py       Screen 2: one borrower's profile & trend
      3_Risk_Drivers.py    Screen 3: point-by-point score & EL explanation
      4_Stress_Test.py      Screen 4: shock sliders, immediate recompute
    theme.py, charts.py, data_pipeline.py, bootstrap.py
  credit/              Pure calculation engine (see below)
    ratios.py, early_warning.py, pd_overlay.py, lgd_overlay.py,
    expected_loss.py, attribution.py, scenarios.py, portfolio.py
  data/                Ingestion, validation, Companies House client
  database/            SQLite schema + helpers (no ORM)
  sample_data/         50-borrower synthetic demo portfolio + generator
  tests/               pytest suite (60+ tests)
  requirements.txt, README.md
```

## The core data model

```
borrower:     borrower_id, company_name, company_number, sector, country
exposure:     loan_id, borrower_id, ead, currency, seniority, maturity,
              baseline_pd, baseline_lgd
financials:   borrower_id, period, revenue, ebitda, debt, cash,
              interest_expense, assets, source
covenants:    loan_id, max_leverage, min_interest_cover, min_liquidity
collateral:   loan_id, collateral_type, value, valuation_date
risk_results: loan_id, date, risk_score, pd, lgd, expected_loss, risk_band
```

Uploads are wide-format (one row per borrower per period, covenants and
collateral attached) for ease of use, then split into these six normalised
tables in SQLite on ingest. Every `financials` row carries a `source` column
(`CUSTOMER_UPLOAD`, `COMPANIES_HOUSE`, or `MANUAL_OVERRIDE`) — provenance is
not optional.

## The calculations, in order

1. **Ratios** (`credit/ratios.py`) — net debt, leverage, net leverage,
   interest cover, EBITDA margin, and period-on-period % changes.
2. **Early-warning scorecard** (`credit/early_warning.py`) — a capped-at-100,
   fully explainable score. Six signal families (EBITDA, Leverage, Interest
   cover, Covenant, Cash, Revenue); within a family only the single
   highest-scoring tier counts, and the total is the sum across families:

   | Signal | Condition | Points |
   |---|---|---|
   | EBITDA | decline >20% | +15 |
   | EBITDA | decline 10–20% | +8 |
   | Leverage | increase >1x | +15 |
   | Leverage | above covenant | +20 |
   | Interest cover | <1.5x | +15 |
   | Interest cover | <1.0x | +20 |
   | Covenant | headroom <10% | +15 |
   | Covenant | breach | +25 |
   | Cash | decline >25% | +10 |
   | Revenue | decline >15% | +8 |

   Bands: 0–24 GREEN, 25–49 AMBER, 50–74 RED, 75–100 CRITICAL.

3. **PD overlay** (`credit/pd_overlay.py`) — a hazard-rate transform turns
   the lender's baseline PD into an indicative stressed PD:
   `lambda = -ln(1-PD0)`, `lambda* = m x lambda`, `PD* = 1 - e^(-lambda*)`,
   where `m` is 1.0 / 1.5 / 2.5 / 4.0 for GREEN / AMBER / RED / CRITICAL.
4. **LGD overlay** (`credit/lgd_overlay.py`) — baseline LGD is uplifted for
   risk-band severity (distressed recoveries are worse) and credited for
   collateral coverage, computed against the loan's *on-record* EAD so that
   a stress-test EAD shock never silently moves LGD.
5. **Expected loss** (`credit/expected_loss.py`) — `EL = EAD x PD x LGD`,
   tracked as both a level and `Delta EL = EL(t) - EL(t-1)`.
6. **Attribution** (`credit/attribution.py`) — Shapley-style decomposition of
   Delta EL into EAD / PD / LGD contributions (the average marginal effect of
   each factor across every order the three could be imagined to change in).
   Contributions always sum exactly to Delta EL.
7. **Stress testing** (`credit/scenarios.py`) — EBITDA, revenue, collateral,
   interest-rate and EAD shocks, recomputing ratios, score, band, PD, LGD and
   EL immediately for the whole portfolio.

## The demo portfolio

`sample_data/demo_portfolio.csv` is a synthetic, reproducible 50-borrower
book across two reporting periods (2026-03-31 and 2026-06-30), generated by
`sample_data/generate_demo_data.py` (fixed random seed). Three borrowers —
**ABC Logistics**, **XYZ Foods** and **Delta Manufacturing** — echo the
illustrative names from the build plan's own mockups, with EAD values
matching it exactly (£18m / £24m / £11m). Their PD, LGD, score and risk band
are **not** hardcoded to match the plan's illustrative mockup figures — they
are computed by the real engine from realistic financials, which is the
entire point of the product. No real companies, real company numbers, or
real financial data are used anywhere in this repository.

## Companies House integration

Optional and off by default. Set the `COMPANIES_HOUSE_API_KEY` environment
variable (get a free key at
https://developer.company-information.service.gov.uk/) to enable live
company lookups from the Borrower screen. Without a key, `data/companies_house.py`
returns a clearly-labelled "not configured" result rather than failing —
the rest of the app works fully on uploaded data alone.

`extract_financials()` prefers [Arelle](https://arelle.org) (an optional
dependency; install `arelle-release` to enable it) for correct iXBRL
taxonomy handling, and falls back to a minimal `lxml`-based tag scraper for a
narrow set of concepts (Revenue, Operating Profit, PBT, Cash, Current
Assets/Liabilities, Total Assets, Creditors, Equity, Employees) when Arelle
isn't installed. It does not attempt to interpret the full Companies House
taxonomy — by design (see the build plan's Week 3 notes).

## Testing

```bash
pytest -v
```

The suite (`tests/`) checks every formula against the build plan's own
worked examples (leverage 4.375x, interest cover 1.6x, EL £486,000, stressed
PD 11.64% at a 2.00x multiplier, scorecard total 60 -> RED), the four Week 6
stress-test regression cases (EBITDA falls / debt falls / collateral
collapses / EAD increases), the Shapley-attribution efficiency property
(contributions always sum exactly to Delta EL) across 200 randomised cases,
and the full `analyse_portfolio()` pipeline end to end on the 50-borrower
demo book.

## Deliberately out of scope (see the build plan, "Scope Discipline")

LLM chatbot, satellite change detection, sophisticated ML, multi-factor Monte
Carlo models, a React frontend, a mobile app, Kubernetes, multi-tenancy,
automated underwriting, portfolio optimisation, ESG scoring, and integration
with dozens of data APIs. Every one of these can consume weeks without
establishing whether a private-credit team will pay for the core product.

## License / status

Founder build plan artifact, prepared August 2026. Not audited, not
regulatory-grade, and not a substitute for professional credit, legal or
investment advice.

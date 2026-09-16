# Credit Transition Monitor

A runnable, explainable Streamlit demonstration for private-credit portfolio teams. Based on the supplied **8-Week Build Plan**, included in `docs/8-Week-Build-Plan.pdf`. No credentials or external services are needed. Bundled data covers **50 fictional borrowers, four quarterly reporting dates and one GBP portfolio**.

> All scorecard thresholds, PD overlays and LGD stress assumptions are uncalibrated prototype choices. This is not a validated regulatory model, an underwriting decision system or investment advice.

## Setup and run

Use Python **3.11 or newer** (tested with Python 3.12). Unzip the project and open a terminal in the `credit-transition-monitor` directory containing this README.

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app/streamlit_app.py
```

Open **http://localhost:8501**. The synthetic demo loads immediately. Network access is only needed to install dependencies; the application itself works offline. Run from the project root to pick up `.streamlit/config.toml`. Stop with Ctrl+C.

The app defaults to light mode and hides the built-in theme menu. Metric cards and the warning banner retain readable dark text even with a previously saved dark theme. Chart text follows the active Streamlit theme. Restart Streamlit after changing its theme configuration.

Tests:

```bash
python -m pytest
python -m pytest --cov=credit_transition_monitor --cov-report=term-missing
```

The engine is an installable package; installation is important. Use the same Python interpreter for installation, Streamlit and tests. Do not add `src` to `sys.path` manually.

```python
from credit_transition_monitor import analyse_portfolio, rank_borrowers
history = analyse_portfolio("sample_data/demo_portfolio.csv")
ranking = rank_borrowers(history)
print(ranking[["company_name", "risk_score", "pd", "lgd", "expected_loss", "delta_el"]])
```

`analyse_portfolio` returns complete calculated history. `rank_borrowers` selects the latest date and ranks by EL deterioration, score, then EL. This preserves history for charts and auditability while delivering the plan's ranking workflow.

## Four screens

- **Portfolio:** EAD, current monitored EL, scenario EL, red/critical counts, EL history, exposure by risk band and sortable/filterable borrower ranking. All summary totals remain portfolio-wide.
- **Borrower:** score, PD, LGD, EL; seven trend charts; three covenant tests and source/calculated history.
- **Risk Drivers:** observations, rule thresholds, individual score points, cap adjustment, hazard-rate arithmetic and exact period-on-period Shapley EL attribution.
- **Stress Test:** independent EBITDA, revenue, collateral and interest-rate sliders, portfolio EL recalculation, borrower impact ranking and scenario Shapley attribution. A downside preset and reset are provided. Scenario values persist when navigating screens.

## Upload contract

Use `sample_data/demo_portfolio.csv` as the template. CSV and XLSX are supported; **only the first XLSX worksheet is read**. Headers are case-insensitive. `PD`, `LGD`, `interest`, `borrower` and `max_leverage_covenant` are accepted aliases for `baseline_pd`, `baseline_lgd`, `interest_expense`, `company_name` and `max_leverage` respectively.

| Required column | Format / interpretation |
|---|---|
| borrower_id | Stable nonblank identifier; exactly one consolidated exposure per borrower/date |
| company_name | Stable nonblank display name |
| period | Reporting date, recommended YYYY-MM-DD |
| currency | One three-letter currency code across the entire upload; no FX conversion |
| ead | Nonnegative exposure at default, currency units |
| baseline_pd | Lender-supplied probability in [0,1], e.g. 0.06, not 6 |
| baseline_lgd | Lender-supplied loss fraction in [0,1] |
| revenue | Strictly positive, currency units |
| ebitda | Finite, may be negative; see conservative handling below |
| debt, cash | Nonnegative, currency units |
| interest_expense | Strictly positive annual interest, currency units |
| max_leverage | Strictly positive maximum debt/EBITDA covenant, multiple |
| min_interest_cover | Strictly positive minimum EBITDA/interest covenant, multiple |
| min_liquidity | Nonnegative minimum cash covenant, currency units |
| collateral_value | Nonnegative valuation, currency units; stressed value reported |

Optional `sector` defaults to Unspecified. Other columns, such as company_number, country, assets and loan_id, are retained but are not used by the risk engine. Company/borrower identifiers are read as strings. No automatic mapping, imputation, hidden row dropping or probability conversion occurs.

All borrowers must appear at all supplied dates (a **balanced panel**). Duplicate borrower/date rows, multiple currencies, blanks, invalid dates, non-finite numeric values and out-of-range probabilities stop analysis with an actionable error. Single-period inputs work, but changes and period attribution are unavailable. Consolidate multiple facilities upstream; do not duplicate borrower financials across loan rows. Use consistent monetary units, annual financial amounts and a common PD horizon. The engine cannot verify those semantic conventions automatically. Financial statement periods are treated as adjacent supplied observations, with no annualisation or quarter-gap correction.

## Methodology and explicit decisions

Full decisions and source-page mapping: [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

Current monitored PD is `1 - (1 - baseline_pd) ** multiplier`, using GREEN 1.0, AMBER 1.5, RED 2.5 and CRITICAL 4.0. Current LGD remains lender supplied. Current EL = EAD × monitored PD × lender LGD. Lender baseline EL is shown separately. Period Δ EL compares monitored EL between adjacent observations for the same borrower. It is not the difference between baseline and overlay EL on the same date.

The maximum raw score is 128; it is capped at 100. Overlapping EBITDA and interest-cover tiers are exclusive within each signal. Covenant-related signals are additive, as separate rows in the plan. Headroom is the smallest of the three relative covenant cushions. Equality with a covenant limit is not a breach.

Negative/zero EBITDA makes leverage undefined. To avoid apparently healthy negative leverage, this MVP conservatively flags the leverage covenant as breached and uses -100% leverage headroom. This is an **additional implementation assumption**; users should review such borrowers. Percentage changes with zero/negative prior values are unavailable and get no trend points, rather than fabricated growth rates.

Stress applies only to the latest reporting date. EBITDA and revenue shocks are independent; no cost model connects them. All debt is assumed floating rate and annual interest moves by debt × bp/10,000; a positive epsilon floor avoids zero division for large downward rate shocks. EAD is fixed.

The LGD stress assumption is `clip(1 - (1 - baseline_lgd) * (1 + collateral_shock), 0, 1)`. It assumes all baseline recovery is collateral-sensitive, does not estimate recovery from collateral/EAD, and is independent of EAD. Thus zero shocks reproduce current EL, collateral-only stress leaves PD unchanged, and EAD-only changes leave LGD unchanged. Collateral increases can reduce LGD. No LGD time-series overlay is invented; historical LGD movement comes from the supplied baseline_lgd observations.

Shapley attribution averages marginal EL effects over **all six calculation orders** of EAD, PD and LGD. Contributions are signed currency amounts and reconcile to total Δ EL. They describe arithmetic contributions, not causal effects. Scorecard points must not be presented as PD Shapley attribution.

## Audit and privacy

The methodology expander on every screen downloads a SQLite database with `normalised_inputs`, `risk_results`, `scenario_results`, `input_provenance` and `run_metadata` tables. Each numeric input has source filename/demo label, borrower, date, value and SHA-256 of the original input bytes. Run metadata records UTC calculation time, model version and scenario. Derived results are identified as CALCULATED at run level and can be reproduced with the included source and inputs. Keep the original input file alongside its hash for byte-level verification.

SQLite is built in memory and exported on demand; customer data is **not automatically persisted on disk**. Uploads are processed locally in the Streamlit process. There is no live Companies House/XBRL connector, no model training and no external data transmission in the application code. Streamlit usage telemetry is disabled in the bundled configuration. Exported audits contain sensitive financial data; treat them like the source portfolio. This prototype has no authentication or multi-user isolation and binds to localhost by default.

## Ten-minute client demo

1. **Minute 1:** open the bundled demo or upload the sample; explain the synthetic-data label.
2. **Minutes 2–3:** Portfolio → sort by EL deterioration and examine borrowers requiring attention.
3. **Minutes 4–5:** Borrower → select the top name; show financial trends and covenant headroom. Risk Drivers → reconcile the points and capped score.
4. **Minutes 6–7:** show baseline-to-monitored PD arithmetic and the EAD/PD/LGD movement attribution.
5. **Minute 8:** Stress Test → set EBITDA to −25%, keeping other sliders at zero to isolate the effect.
6. **Minute 9:** show portfolio EL uplift, then add collateral/rate shocks and inspect the LGD contribution.
7. **Minute 10:** download the audit trail and discuss the client's monitoring workflow.

## Scope

Implements the requested financial-monitoring MVP from Weeks 1, 2, 4, 5 and 6, and the Week 7 demo flow. The plan's **Week 3 live Companies House and Arelle ingestion** is not implemented in this offline deliverable; no public-data enrichment is simulated or claimed. Customer discovery, automated weekly reporting and production hosting are also outside this build. No satellite, ML, LLM chatbot, React, Kubernetes or additional product layers.

## Structure

```text
app/streamlit_app.py               Presentation and interaction only
src/credit_transition_monitor/     Validation, ratios, changes, covenants,
                                  scorecard, PD, EL, scenarios, attribution, audit
tests/                            Engine, validation, audit and app interaction tests
sample_data/                      Demo CSV and deterministic generator
docs/                             Source PDF, methodology and verification record
.streamlit/config.toml            Theme, local binding and telemetry settings
pyproject.toml                     Installable package and dependencies
requirements.txt                  Editable install including test dependencies
```

Technical references used for app verification: [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) and [Plotly chart rendering](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart). Model choices are taken from the supplied plan, not from those technical references.

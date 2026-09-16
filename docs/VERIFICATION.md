# Verification record

Verified on 16 September 2026 with Python 3.12.14 on macOS.

- Installed the src-layout package in an isolated virtual environment.
- **105 pytest tests passed**, including all four screens through Streamlit AppTest.
- Engine statement coverage: **99%** (257 of 258 statements; coverage is not model validation).
- CSV and XLSX ingestion round trips, malformed inputs, duplicate identifiers/headers, mixed currencies and unbalanced dates tested.
- Boundary score rules, capped totals, PD 0/1 endpoints, negative EBITDA, covenant equality, zero-history cases tested.
- Zero-scenario identity, collateral-only/EBITDA/rate/EAD behavior and Shapley reconciliations tested.
- Scenario persistence across navigation, reset button and upload empty state exercised.
- SQLite export reopened and its metadata/provenance verified.
- Streamlit server launched on localhost; portfolio and risk-driver layouts visually inspected. Initial clipping and negative-zero presentation corrected.

## Reproducible demo checks

- 50 borrowers; 200 observations; four dates.
- Current EAD: GBP 1,275,886,156.12.
- Current monitored EL: GBP 32,500,074.34.
- Period EL movement: GBP 7,891,889.83.
- EBITDA-only −25% scenario EL: GBP 47,733,998.98.
- Scenario uplift: GBP 15,233,924.63.

Use `python -m pytest --cov=credit_transition_monitor --cov-report=term-missing` to reproduce tests. Direct dependency versions are recorded in `constraints-tested.txt`; optionally install with `python -m pip install -r requirements.txt -c constraints-tested.txt`.

No claim of production certification, security audit, regulatory calibration or economic backtesting is made. Live Companies House enrichment is not implemented. See README and methodology for scope and assumptions.

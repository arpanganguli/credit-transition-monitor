"""
credit
======

Pure, dependency-light calculation engine for the Early-Warning & Loss Monitor.

Every function in this package is deterministic and unit-testable: given the
same inputs it always returns the same outputs, with no hidden state, no I/O,
and no calls to Streamlit. This is deliberate -- it is what lets a credit
analyst reproduce every number the dashboard shows.

Modules
-------
ratios          Borrower-level financial ratios (leverage, interest cover, ...)
pd_overlay      Hazard-rate transform of a baseline PD into an indicative stressed PD
lgd_overlay     Risk-band / collateral-aware adjustment of a baseline LGD
expected_loss   EL = EAD x PD x LGD, and period-on-period Delta EL
early_warning   The capped-at-100 explainable scorecard and risk bands
attribution     Shapley-style decomposition of Delta EL into EAD/PD/LGD drivers
scenarios       Stress-testing engine (EBITDA/revenue/collateral/rate/EAD shocks)
portfolio       High-level orchestration: analyse_portfolio() end to end

IMPORTANT: scorecard thresholds, risk-band multipliers and pilot pricing are
prototype assumptions to test with users -- not statistically calibrated
probabilities of default, not regulatory-model output, and not investment
advice. See README.md.
"""

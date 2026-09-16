# Model specification and provenance

Source: `8-Week-Build-Plan.pdf`, supplied by the user; August 2026. Model ID: `week2-v1.0`. The PDF is the primary requirements source, not a claim of validated methodology.

| Component | Source | Implementation |
|---|---|---|
| Financial ratios and EL | pp. 3–4, Week 1 | Net debt, leverage, net leverage, interest cover, EBITDA margin; EAD × PD × LGD |
| Adjacent period changes | p. 4 and existing project direction | Absolute changes in EBITDA/revenue/leverage/cover/cash; relative changes in EBITDA/revenue/cash |
| Scorecard and bands | p. 5, Week 2 | Exact points below, cap 100 |
| Hazard overlay | p. 5, Week 2 | Stable `-expm1(multiplier * log1p(-PD0))`, including PD 0 and 1 |
| Four screens | p. 7, Week 4 | Portfolio, Borrower, Risk Drivers, Stress Test |
| Shapley attribution | p. 7, Week 5 | Exact six-order averaging for period and scenario EL movements |
| Behavioral validation/audit | pp. 7–8, Week 6 | Automated tests, source hash, field lineage, downloadable SQLite |
| Demo flow | p. 9 | README ten-minute walkthrough |

## Score rules

| Signal | Rule | Points |
|---|---|---:|
| EBITDA | Decline greater than 20% | 15 |
| EBITDA | Decline 10% to 20%, inclusive | 8 |
| Leverage | Absolute increase greater than 1.0× | 15 |
| Leverage | Above its maximum covenant | 20 |
| Interest cover | Below 1.0× | 20 |
| Interest cover | At least 1.0× but below 1.5× | 15 |
| Minimum covenant headroom | Below 10% | 15 |
| Any covenant | Breached | 25 |
| Cash | Decline greater than 25% | 10 |
| Revenue | Decline greater than 15% | 8 |

Both EBITDA rows are alternative tiers; both interest-cover rows are alternative tiers. Other signals add, including covenant breach, leverage breach and low headroom. The PDF does not explicitly resolve overlapping tiers; this implementation uses the highest applicable tier and documents the choice. Raw total can reach 128. Score = min(raw total, 100).

GREEN 0–24 (1.0×); AMBER 25–49 (1.5×); RED 50–74 (2.5×); CRITICAL 75–100 (4.0×). The Week 6 illustrative RED multiplier of 2.0 differs from the Week 2 rule table; **Week 2 governs**. Dashboard/example numerical values in the PDF are illustrative, not fixtures that the synthetic demo must match.

## Headroom

- Leverage: `(maximum − actual) / maximum`.
- Interest cover: `(actual − minimum) / minimum`.
- Liquidity: `(cash − minimum cash) / minimum cash`.
- Overall: smallest available cushion. A zero liquidity minimum has no finite relative headroom and is omitted from this minimum; cash >= 0 meets that covenant.
- A ratio exactly at its limit is not a breach, but has zero headroom and triggers the <10% headroom rule.
- Non-positive EBITDA: undefined leverage, assumed leverage breach and -100% leverage cushion. Explicit conservative extension, not a rule stated by the PDF.

## Missing data and chronology

Required inputs must be finite and complete. No carry-forward or mean imputation. First-observation trend values are unavailable and have zero points; static covenant/cover rules still apply. Percentage changes are only computed against positive previous amounts. These choices can understate risk when history is absent, so the UI identifies single-period portfolios and non-positive EBITDA. Date spacing and PD horizon consistency are supplied by the user; the engine does not infer them.

## Stress and EL semantics

Baseline EL means lender EAD × lender PD × lender LGD. Current EL means lender EAD × hazard-overlay PD × lender LGD. Scenario EL uses shocked latest financial inputs and LGD recovery assumption. Period attribution compares current monitored EL to previous monitored EL, whereas scenario attribution compares scenario EL to current monitored EL on the same date. They are separate decompositions.

LGD recovery haircuts are an explicit extension required to make the requested collateral slider useful: `LGD* = clip(1 − (1 − LGD0) × (1 + collateral shock), 0, 1)`. All baseline recovery is assumed collateral-sensitive. Absolute collateral valuation is recorded and shocked for audit but does not determine baseline LGD. Zero LGD with a collateral haircut can become positive under this assumption. At a 100% collateral loss, LGD becomes 100%. The model is independent of EAD, preserving the Week 6 EAD-only invariant.

All debt is assumed floating-rate, with annual interest-rate shocks. EBITDA and revenue shocks are independent and apply to latest supplied figures. Cash, EAD and covenants stay fixed. Scenario changes can cross discrete score bands, so small shocks need not change PD/EL. In particular, "EBITDA down ⇒ PD up" is weakly monotone and only strictly increases PD when a higher band is reached. The tests check this distinction rather than promising a smooth calibrated response.

## Deferred scope

Companies House/Arelle ingestion in Week 3 needs separate live-data work and is not present. Provenance describes the actual CSV/XLSX or synthetic source only. No manual override interface or external financial-source claims. Multiple facilities, entrants/exits, mixed currencies, regulatory calibration and authentication are not supported. Input restrictions are enforced rather than silently double-counting or combining incomparable amounts.

"""
Generate the 50-borrower synthetic demo portfolio (two reporting periods)
used throughout the app and the test suite.

Run this script to regenerate sample_data/demo_portfolio.csv from scratch:

    python3 sample_data/generate_demo_data.py

The output is a single wide-format CSV, one row per (borrower, period), with
the borrower/exposure/financials/covenant/collateral fields the rest of the
product expects (see credit/portfolio.py and data/validation.py).

Three borrowers -- ABC Logistics, XYZ Foods and Delta Mfg -- are hand-crafted
to echo the illustrative names used throughout the build plan's own mockups,
with EAD values matching the plan exactly (£18m / £24m / £11m). Their PD,
LGD, score and risk band are NOT hardcoded to match the plan's mockup
figures -- those are computed by the actual engine (credit/portfolio.py) from
these financials, which is the entire point of the product: every number is
reproducible from a formula, not typed in. The remaining 47 borrowers are
randomly generated with a fixed seed for reproducibility.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

SEED = 20260615
PERIOD_PREVIOUS = "2026-03-31"
PERIOD_CURRENT = "2026-06-30"

SECTORS = [
    "Business Services",
    "Specialty Manufacturing",
    "Healthcare Services",
    "Food & Beverage",
    "Logistics & Distribution",
    "Technology & Software",
    "Specialty Retail",
    "Construction & Building Products",
    "Hospitality & Leisure",
    "Industrials",
]

COLLATERAL_TYPES = [
    "All-asset debenture",
    "Real estate",
    "Inventory & receivables",
    "Plant & equipment",
    "Unsecured",
]

OUT_PATH = Path(__file__).resolve().parent / "demo_portfolio.csv"

FIELDNAMES = [
    "borrower_id",
    "company_name",
    "sector",
    "country",
    "company_number",
    "loan_id",
    "seniority",
    "maturity",
    "period",
    "ead",
    "baseline_pd",
    "baseline_lgd",
    "revenue",
    "ebitda",
    "debt",
    "cash",
    "interest_expense",
    "assets",
    "max_leverage",
    "min_interest_cover",
    "min_liquidity",
    "collateral_type",
    "collateral_value",
    "valuation_date",
]


def _row(
    borrower_id,
    company_name,
    sector,
    company_number,
    loan_id,
    seniority,
    maturity,
    period,
    ead,
    baseline_pd,
    baseline_lgd,
    revenue,
    ebitda,
    debt,
    cash,
    interest_expense,
    assets,
    max_leverage,
    min_interest_cover,
    min_liquidity,
    collateral_type,
    collateral_value,
    valuation_date,
):
    return {
        "borrower_id": borrower_id,
        "company_name": company_name,
        "sector": sector,
        "country": "United Kingdom",
        "company_number": company_number,
        "loan_id": loan_id,
        "seniority": seniority,
        "maturity": maturity,
        "period": period,
        "ead": round(ead, 2),
        "baseline_pd": round(baseline_pd, 4),
        "baseline_lgd": round(baseline_lgd, 4),
        "revenue": round(revenue, 2),
        "ebitda": round(ebitda, 2),
        "debt": round(debt, 2),
        "cash": round(cash, 2),
        "interest_expense": round(interest_expense, 2),
        "assets": round(assets, 2),
        "max_leverage": round(max_leverage, 2),
        "min_interest_cover": round(min_interest_cover, 2),
        "min_liquidity": round(min_liquidity, 2),
        "collateral_type": collateral_type,
        "collateral_value": round(collateral_value, 2),
        "valuation_date": valuation_date,
    }


def _flagship_borrowers() -> list[dict]:
    """
    The three named borrowers echoed from the build plan's own dashboard
    mockups. Financials are hand-set so the *engine* (not a hardcoded
    number) produces a materially deteriorating, low-headroom credit --
    exactly the story the build plan tells about them.
    """
    rows = []

    # ABC Logistics: EAD £18m, sharp EBITDA decline, leverage breaches covenant.
    rows += [
        _row(
            "BRW-001", "ABC Logistics Ltd", "Logistics & Distribution", "SYN100001",
            "LN-001", "Senior secured", "2028-09-30", PERIOD_PREVIOUS,
            ead=18_000_000, baseline_pd=0.030, baseline_lgd=0.42,
            revenue=62_000_000, ebitda=8_400_000, debt=34_440_000, cash=5_200_000,
            interest_expense=3_050_000, assets=41_000_000,
            max_leverage=5.00, min_interest_cover=1.75, min_liquidity=2_000_000,
            collateral_type="All-asset debenture", collateral_value=12_600_000,
            valuation_date="2026-01-15",
        ),
        _row(
            "BRW-001", "ABC Logistics Ltd", "Logistics & Distribution", "SYN100001",
            "LN-001", "Senior secured", "2028-09-30", PERIOD_CURRENT,
            ead=18_900_000, baseline_pd=0.030, baseline_lgd=0.42,
            revenue=51_400_000, ebitda=6_390_000, debt=35_800_000, cash=3_500_000,
            interest_expense=3_180_000, assets=39_500_000,
            max_leverage=5.00, min_interest_cover=1.75, min_liquidity=2_000_000,
            collateral_type="All-asset debenture", collateral_value=12_600_000,
            valuation_date="2026-01-15",
        ),
    ]

    # XYZ Foods: EAD £24m, moderate deterioration -- lands in RED, not CRITICAL.
    rows += [
        _row(
            "BRW-002", "XYZ Foods Ltd", "Food & Beverage", "SYN100002",
            "LN-002", "Unitranche", "2029-03-31", PERIOD_PREVIOUS,
            ead=23_500_000, baseline_pd=0.028, baseline_lgd=0.38,
            revenue=88_000_000, ebitda=11_700_000, debt=40_600_000, cash=6_800_000,
            interest_expense=4_100_000, assets=58_000_000,
            max_leverage=4.25, min_interest_cover=2.00, min_liquidity=3_000_000,
            collateral_type="Inventory & receivables", collateral_value=17_200_000,
            valuation_date="2026-01-20",
        ),
        _row(
            "BRW-002", "XYZ Foods Ltd", "Food & Beverage", "SYN100002",
            "LN-002", "Unitranche", "2029-03-31", PERIOD_CURRENT,
            ead=24_000_000, baseline_pd=0.028, baseline_lgd=0.38,
            revenue=81_000_000, ebitda=9_650_000, debt=41_900_000, cash=5_900_000,
            interest_expense=4_260_000, assets=56_500_000,
            max_leverage=4.25, min_interest_cover=2.00, min_liquidity=3_000_000,
            collateral_type="Inventory & receivables", collateral_value=17_200_000,
            valuation_date="2026-01-20",
        ),
    ]

    # Delta Mfg: EAD £11m, mild deterioration -- lower on the RED band.
    rows += [
        _row(
            "BRW-003", "Delta Manufacturing Ltd", "Specialty Manufacturing", "SYN100003",
            "LN-003", "Senior secured", "2027-12-31", PERIOD_PREVIOUS,
            ead=10_700_000, baseline_pd=0.025, baseline_lgd=0.36,
            revenue=39_000_000, ebitda=5_460_000, debt=17_900_000, cash=2_600_000,
            interest_expense=1_640_000, assets=26_000_000,
            max_leverage=3.75, min_interest_cover=2.25, min_liquidity=1_200_000,
            collateral_type="Plant & equipment", collateral_value=8_100_000,
            valuation_date="2026-02-01",
        ),
        _row(
            "BRW-003", "Delta Manufacturing Ltd", "Specialty Manufacturing", "SYN100003",
            "LN-003", "Senior secured", "2027-12-31", PERIOD_CURRENT,
            ead=11_000_000, baseline_pd=0.025, baseline_lgd=0.36,
            revenue=36_500_000, ebitda=4_820_000, debt=18_400_000, cash=2_150_000,
            interest_expense=1_700_000, assets=25_400_000,
            max_leverage=3.75, min_interest_cover=2.25, min_liquidity=1_200_000,
            collateral_type="Plant & equipment", collateral_value=8_100_000,
            valuation_date="2026-02-01",
        ),
    ]

    return rows


def _random_borrowers(n: int, rng: np.random.Generator) -> list[dict]:
    rows = []
    tiers = list(_TIER_WEIGHTS.keys())
    weights = list(_TIER_WEIGHTS.values())
    tier_assignment = rng.choice(tiers, size=n, p=weights)

    for i in range(n):
        idx = i + 4  # borrower numbering continues after the three flagships
        borrower_id = f"BRW-{idx:03d}"
        sector = SECTORS[i % len(SECTORS)]
        company_name = f"{sector.split(' ')[0]} Portfolio Co {idx} Ltd"
        company_number = f"SYN1{idx:05d}"
        loan_id = f"LN-{idx:03d}"

        revenue0 = float(np.exp(rng.normal(np.log(28_000_000), 0.55)))
        margin0 = float(rng.uniform(0.09, 0.24))
        ebitda0 = revenue0 * margin0
        leverage0 = float(rng.uniform(2.2, 4.3))
        debt0 = ebitda0 * leverage0
        cash0 = revenue0 * float(rng.uniform(0.03, 0.09))
        rate0 = float(rng.uniform(0.055, 0.095))
        interest0 = debt0 * rate0
        assets0 = revenue0 * float(rng.uniform(0.9, 1.6))
        ead0 = debt0 * float(rng.uniform(0.45, 0.95))

        baseline_pd = float(rng.uniform(0.012, 0.045))
        baseline_lgd = float(rng.uniform(0.28, 0.48))

        max_leverage = leverage0 * float(rng.uniform(1.15, 1.35))
        min_interest_cover = (ebitda0 / interest0) * float(rng.uniform(0.5, 0.72))
        min_liquidity = cash0 * float(rng.uniform(0.25, 0.55))

        collateral_type = COLLATERAL_TYPES[i % len(COLLATERAL_TYPES)]
        coverage = 0.0 if collateral_type == "Unsecured" else float(rng.uniform(0.35, 1.25))
        collateral_value = ead0 * coverage

        tier = tier_assignment[i]
        params = _TIER_PARAMS[tier]
        ebitda_mult = float(rng.uniform(*params["ebitda"]))
        revenue_mult = float(rng.uniform(*params["revenue"]))
        cash_mult = float(rng.uniform(*params["cash"]))
        debt_mult = float(rng.uniform(*params["debt"]))
        rate_bump = float(rng.uniform(*params["rate_bump"]))

        revenue1 = revenue0 * revenue_mult
        ebitda1 = ebitda0 * ebitda_mult
        debt1 = debt0 * debt_mult
        cash1 = cash0 * cash_mult
        rate1 = rate0 + rate_bump
        interest1 = debt1 * rate1
        assets1 = assets0 * float(rng.uniform(0.97, 1.05))
        ead1 = ead0 * float(rng.uniform(0.97, 1.06))

        common = dict(
            borrower_id=borrower_id,
            company_name=company_name,
            sector=sector,
            company_number=company_number,
            loan_id=loan_id,
            seniority="Senior secured" if collateral_type != "Unsecured" else "Unsecured",
            maturity="2028-06-30",
            baseline_pd=baseline_pd,
            baseline_lgd=baseline_lgd,
            max_leverage=max_leverage,
            min_interest_cover=min_interest_cover,
            min_liquidity=min_liquidity,
            collateral_type=collateral_type,
            collateral_value=collateral_value,
            valuation_date="2026-02-01",
        )

        rows.append(
            _row(
                period=PERIOD_PREVIOUS, ead=ead0, revenue=revenue0, ebitda=ebitda0,
                debt=debt0, cash=cash0, interest_expense=interest0, assets=assets0, **common,
            )
        )
        rows.append(
            _row(
                period=PERIOD_CURRENT, ead=ead1, revenue=revenue1, ebitda=ebitda1,
                debt=debt1, cash=cash1, interest_expense=interest1, assets=assets1, **common,
            )
        )

    return rows


_TIER_PARAMS = {
    "severe": dict(ebitda=(0.50, 0.72), revenue=(0.65, 0.85), cash=(0.40, 0.60), debt=(1.10, 1.25), rate_bump=(0.012, 0.025)),
    "moderate": dict(ebitda=(0.81, 0.90), revenue=(0.86, 0.96), cash=(0.68, 0.86), debt=(1.00, 1.07), rate_bump=(0.002, 0.008)),
    "mild": dict(ebitda=(0.79, 0.90), revenue=(0.90, 1.02), cash=(0.72, 0.90), debt=(1.00, 1.09), rate_bump=(0.0, 0.007)),
    "stable": dict(ebitda=(0.97, 1.15), revenue=(0.97, 1.12), cash=(0.90, 1.18), debt=(0.85, 1.02), rate_bump=(0.0, 0.0)),
}
# Tier probabilities: most of the book is stable; a deliberate tail
# deteriorates across mild -> moderate -> severe, so the demo shows a full
# spread of risk bands rather than a bimodal "fine or on fire" portfolio.
_TIER_WEIGHTS = {"stable": 0.60, "mild": 0.18, "moderate": 0.14, "severe": 0.08}


def generate() -> list[dict]:
    rng = np.random.default_rng(SEED)
    rows = _flagship_borrowers() + _random_borrowers(47, rng)
    return rows


def main() -> None:
    rows = generate()
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows ({len(rows)//2} borrowers x 2 periods) to {OUT_PATH}")


if __name__ == "__main__":
    main()

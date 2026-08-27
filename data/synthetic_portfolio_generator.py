import numpy as np
import pandas as pd


def create_synthetic_portfolio(
    n_borrowers: int = 30,
    seed: int = 42
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    sectors = [
        "Industrials",
        "Technology",
        "Healthcare",
        "Consumer",
        "Logistics",
        "Business Services",
        "Manufacturing",
    ]

    rows: list[dict[str, object]] = []

    for i in range(1, n_borrowers + 1):
        borrower_id = f"B{i:03d}"
        borrower_name = f"Borrower {i:03d}"
        sector = rng.choice(sectors)

        # -----------------------------
        # Initial reporting period
        # -----------------------------
        revenue_t0 = rng.uniform(20_000_000, 200_000_000)

        ebitda_margin_t0 = rng.uniform(0.08, 0.30)
        ebitda_t0 = revenue_t0 * ebitda_margin_t0

        leverage_t0 = rng.uniform(2.0, 6.0)
        debt_t0 = ebitda_t0 * leverage_t0

        cash_t0 = rng.uniform(0.03, 0.15) * revenue_t0

        interest_rate_t0 = rng.uniform(0.05, 0.10)
        interest_expense_t0 = debt_t0 * interest_rate_t0

        ead_t0 = debt_t0 * rng.uniform(0.70, 1.00)

        pd_t0 = rng.uniform(0.005, 0.08)
        lgd_t0 = rng.uniform(0.25, 0.60)

        # Covenants
        max_leverage = leverage_t0 + rng.uniform(0.3, 1.5)
        min_interest_cover = rng.uniform(1.2, 2.5)
        min_liquidity = rng.uniform(1_000_000, 10_000_000)

        rows.append({
            "borrower_id": borrower_id,
            "borrower_name": borrower_name,
            "sector": sector,
            "period": "2025-12-31",
            "ead": ead_t0,
            "pd": pd_t0,
            "lgd": lgd_t0,
            "revenue": revenue_t0,
            "ebitda": ebitda_t0,
            "debt": debt_t0,
            "cash": cash_t0,
            "interest_expense": interest_expense_t0,
            "max_leverage_covenant": max_leverage,
            "min_interest_cover_covenant": min_interest_cover,
            "min_liquidity_covenant": min_liquidity,
        })

        # -----------------------------
        # Second reporting period
        # -----------------------------

        # Most borrowers move modestly,
        # while some are deliberately stressed.
        stressed = rng.random() < 0.30

        if stressed:
            revenue_growth = rng.uniform(-0.25, -0.05)
            ebitda_growth = rng.uniform(-0.40, -0.10)
            debt_growth = rng.uniform(0.00, 0.20)
            cash_growth = rng.uniform(-0.40, -0.10)
            rate_change = rng.uniform(0.005, 0.03)
        else:
            revenue_growth = rng.uniform(-0.05, 0.12)
            ebitda_growth = rng.uniform(-0.08, 0.15)
            debt_growth = rng.uniform(-0.10, 0.08)
            cash_growth = rng.uniform(-0.10, 0.20)
            rate_change = rng.uniform(-0.005, 0.01)

        revenue_t1 = revenue_t0 * (1 + revenue_growth)
        ebitda_t1 = max(
            ebitda_t0 * (1 + ebitda_growth),
            100_000
        )

        debt_t1 = max(
            debt_t0 * (1 + debt_growth),
            0
        )

        cash_t1 = max(
            cash_t0 * (1 + cash_growth),
            0
        )

        interest_rate_t1 = max(
            interest_rate_t0 + rate_change,
            0.01
        )

        interest_expense_t1 = debt_t1 * interest_rate_t1

        ead_t1 = max(
            ead_t0 * rng.uniform(0.95, 1.05),
            0
        )

        # Keep PD/LGD as baseline credit inputs for now.
        # Later your model can generate stressed versions.
        pd_t1 = pd_t0
        lgd_t1 = lgd_t0

        rows.append({
            "borrower_id": borrower_id,
            "borrower_name": borrower_name,
            "sector": sector,
            "period": "2026-06-30",
            "ead": ead_t1,
            "pd": pd_t1,
            "lgd": lgd_t1,
            "revenue": revenue_t1,
            "ebitda": ebitda_t1,
            "debt": debt_t1,
            "cash": cash_t1,
            "interest_expense": interest_expense_t1,
            "max_leverage_covenant": max_leverage,
            "min_interest_cover_covenant": min_interest_cover,
            "min_liquidity_covenant": min_liquidity,
        })

    df = pd.DataFrame(rows)

    df["period"] = pd.to_datetime(df["period"])

    return df
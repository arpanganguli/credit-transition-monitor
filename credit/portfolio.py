"""
High-level orchestration: turn raw borrower financials into a fully-scored,
fully-explained portfolio DataFrame.

The headline entry point is ``analyse_portfolio``, which matches the Week 1
"definition of done" from the build plan almost verbatim:

    run analyse_portfolio("portfolio.csv") on a 50-borrower synthetic
    portfolio and return a DataFrame ranked by expected-loss deterioration

It accepts either:

  * a minimal single-period CSV with columns
    ``borrower, EAD, PD, LGD, revenue, EBITDA, debt, cash, interest``
    (exactly the Week 1 worked example), in which case there is no prior
    period to compare against and the ranking falls back to EL descending; or

  * a richer, long-format CSV with one row per (borrower, period) and the
    full core data model's columns (see database/schema.py and
    sample_data/demo_portfolio.csv) -- the format the Streamlit app uses --
    in which case each borrower's *latest* period is compared against its
    *previous* period and the ranking is by Delta EL descending (biggest
    deteriorations first).
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from credit import ratios as ratios_mod
from credit.attribution import attribute_delta_el
from credit.early_warning import compute_scorecard
from credit.expected_loss import delta_expected_loss, delta_expected_loss_pct, expected_loss
from credit.lgd_overlay import stressed_lgd
from credit.pd_overlay import stressed_pd_from_band

# Aliases so we can accept the exact minimal Week-1 CSV header as well as the
# richer core-data-model column names, case-insensitively.
_COLUMN_ALIASES = {
    "borrower": "borrower_id",
    "borrower_id": "borrower_id",
    "company": "company_name",
    "company_name": "company_name",
    "ead": "ead",
    "pd": "baseline_pd",
    "baseline_pd": "baseline_pd",
    "lgd": "baseline_lgd",
    "baseline_lgd": "baseline_lgd",
    "revenue": "revenue",
    "ebitda": "ebitda",
    "debt": "debt",
    "cash": "cash",
    "interest": "interest_expense",
    "interest_expense": "interest_expense",
    "period": "period",
    "max_leverage": "max_leverage",
    "min_interest_cover": "min_interest_cover",
    "min_liquidity": "min_liquidity",
    "collateral_value": "collateral_value",
    "sector": "sector",
    "country": "country",
    "company_number": "company_number",
    "loan_id": "loan_id",
    "seniority": "seniority",
    "maturity": "maturity",
}

REQUIRED_COLUMNS = [
    "borrower_id",
    "ead",
    "baseline_pd",
    "baseline_lgd",
    "revenue",
    "ebitda",
    "debt",
    "cash",
    "interest_expense",
]


def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case and alias-map columns so either CSV shape works."""
    rename = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in _COLUMN_ALIASES:
            rename[col] = _COLUMN_ALIASES[key]
    return df.rename(columns=rename)


def _row_to_financials(row: pd.Series) -> dict:
    return {
        "revenue": row.get("revenue"),
        "ebitda": row.get("ebitda"),
        "debt": row.get("debt"),
        "cash": row.get("cash"),
        "interest_expense": row.get("interest_expense"),
    }


def process_borrower_period(
    borrower_id: str,
    current: dict,
    previous: Optional[dict],
    covenants: Optional[dict] = None,
    collateral_value: Optional[float] = None,
    extra: Optional[dict] = None,
) -> dict:
    """
    Run the full pipeline for one borrower's latest period vs. its previous
    period (if any): ratios, period changes, the early-warning scorecard,
    stressed PD/LGD, EL, Delta EL, and (when a previous period exists) the
    Shapley attribution of Delta EL into EAD/PD/LGD contributions.
    """
    covenants = covenants or {}
    extra = extra or {}

    current_fin = _row_to_financials(current)
    previous_fin = _row_to_financials(previous) if previous else None

    curr_ratios = ratios_mod.compute_ratios(**current_fin)
    changes = ratios_mod.compute_period_changes(current_fin, previous_fin)

    max_leverage = covenants.get("max_leverage")
    min_interest_cover = covenants.get("min_interest_cover")
    min_liquidity = covenants.get("min_liquidity")

    headrooms = []
    breached = False
    if max_leverage and curr_ratios.leverage is not None and max_leverage > 0:
        headrooms.append((max_leverage - curr_ratios.leverage) / max_leverage)
        if curr_ratios.leverage > max_leverage:
            breached = True
    if min_interest_cover and curr_ratios.interest_cover is not None:
        if min_interest_cover > 0:
            headrooms.append((curr_ratios.interest_cover - min_interest_cover) / min_interest_cover)
        if curr_ratios.interest_cover < min_interest_cover:
            breached = True
    if min_liquidity and current_fin.get("cash") is not None:
        if min_liquidity > 0:
            headrooms.append((current_fin["cash"] - min_liquidity) / min_liquidity)
        if current_fin["cash"] < min_liquidity:
            breached = True
    headroom = min(headrooms) if headrooms else None

    scorecard = compute_scorecard(
        ebitda_change=changes.ebitda_change,
        leverage_change=changes.leverage_change,
        leverage_current=curr_ratios.leverage,
        max_leverage=max_leverage,
        interest_cover_current=curr_ratios.interest_cover,
        covenant_headroom=headroom,
        covenant_breached=breached,
        cash_change=changes.cash_change,
        revenue_change=changes.revenue_change,
    )

    ead = current.get("ead")
    baseline_pd = current.get("baseline_pd")
    baseline_lgd = current.get("baseline_lgd")

    pd_stressed = stressed_pd_from_band(baseline_pd, scorecard.band)
    lgd_stressed = stressed_lgd(
        baseline_lgd, scorecard.band, collateral_value=collateral_value, ead_baseline=ead
    )
    el = expected_loss(ead, pd_stressed, lgd_stressed)

    result = {
        "borrower_id": borrower_id,
        **extra,
        "ead": ead,
        "revenue": current_fin["revenue"],
        "ebitda": current_fin["ebitda"],
        "debt": current_fin["debt"],
        "cash": current_fin["cash"],
        "interest_expense": current_fin["interest_expense"],
        **curr_ratios.to_dict(),
        **changes.to_dict(),
        "baseline_pd": baseline_pd,
        "baseline_lgd": baseline_lgd,
        "pd": pd_stressed,
        "lgd": lgd_stressed,
        "expected_loss": el,
        "score": scorecard.score,
        "risk_band": scorecard.band.value,
        "reasons": scorecard.reasons,
        "covenant_headroom": headroom,
        "covenant_breached": breached,
        "max_leverage": max_leverage,
        "min_interest_cover": min_interest_cover,
        "min_liquidity": min_liquidity,
        "collateral_value": collateral_value,
    }

    if previous:
        prev_ead = previous.get("ead", ead)
        prev_pd0 = previous.get("baseline_pd", baseline_pd)
        prev_lgd0 = previous.get("baseline_lgd", baseline_lgd)

        # The previous period's own risk band, scored on a "no prior data"
        # basis (i.e. against covenants/levels only) unless an even-earlier
        # period was supplied via extra["previous_of_previous"].
        prev_scorecard = compute_scorecard(
            ebitda_change=None,
            leverage_change=None,
            leverage_current=ratios_mod.leverage(previous_fin["debt"], previous_fin["ebitda"]),
            max_leverage=max_leverage,
            interest_cover_current=ratios_mod.interest_cover(
                previous_fin["ebitda"], previous_fin["interest_expense"]
            ),
            covenant_headroom=None,
            covenant_breached=False,
            cash_change=None,
            revenue_change=None,
        )
        prev_pd_stressed = stressed_pd_from_band(prev_pd0, prev_scorecard.band)
        prev_lgd_stressed = stressed_lgd(
            prev_lgd0, prev_scorecard.band, collateral_value=collateral_value, ead_baseline=prev_ead
        )
        el_previous = expected_loss(prev_ead, prev_pd_stressed, prev_lgd_stressed)

        attribution = attribute_delta_el(
            ead_baseline=prev_ead,
            pd_baseline=prev_pd_stressed,
            lgd_baseline=prev_lgd_stressed,
            ead_current=ead,
            pd_current=pd_stressed,
            lgd_current=lgd_stressed,
        )

        result["expected_loss_previous"] = el_previous
        result["delta_el"] = delta_expected_loss(el, el_previous)
        result["delta_el_pct"] = delta_expected_loss_pct(el, el_previous)
        result["attribution_ead"] = attribution.contributions["ead"]
        result["attribution_pd"] = attribution.contributions["pd"]
        result["attribution_lgd"] = attribution.contributions["lgd"]
        result["pd_previous"] = prev_pd_stressed
        result["lgd_previous"] = prev_lgd_stressed
        result["leverage_previous"] = ratios_mod.leverage(previous_fin["debt"], previous_fin["ebitda"])
        result["interest_cover_previous"] = ratios_mod.interest_cover(
            previous_fin["ebitda"], previous_fin["interest_expense"]
        )
        result["revenue_previous"] = previous_fin["revenue"]
        result["ebitda_previous"] = previous_fin["ebitda"]
        result["debt_previous"] = previous_fin["debt"]
        result["cash_previous"] = previous_fin["cash"]
        result["interest_expense_previous"] = previous_fin["interest_expense"]
    else:
        result["expected_loss_previous"] = None
        result["delta_el"] = None
        result["delta_el_pct"] = None
        result["attribution_ead"] = None
        result["attribution_pd"] = None
        result["attribution_lgd"] = None
        result["pd_previous"] = None
        result["lgd_previous"] = None
        result["leverage_previous"] = None
        result["interest_cover_previous"] = None
        result["revenue_previous"] = None
        result["ebitda_previous"] = None
        result["debt_previous"] = None
        result["cash_previous"] = None
        result["interest_expense_previous"] = None

    return result


def analyse_portfolio_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full pipeline over an already-loaded, already-normalised DataFrame.

    Expects one row per (borrower_id, period) at minimum; covenant and
    collateral columns are optional. Returns one row per borrower (the latest
    period), ranked by expected-loss deterioration (Delta EL descending when
    available, otherwise EL descending).
    """
    df = normalise_columns(df)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")

    has_period = "period" in df.columns and df["period"].notna().any()

    rows = []
    for borrower_id, group in df.groupby("borrower_id", sort=False):
        if has_period:
            group = group.sort_values("period")
        current = group.iloc[-1].to_dict()
        previous = group.iloc[-2].to_dict() if len(group) > 1 else None

        covenants = {
            "max_leverage": current.get("max_leverage"),
            "min_interest_cover": current.get("min_interest_cover"),
            "min_liquidity": current.get("min_liquidity"),
        }
        collateral_value = current.get("collateral_value")

        extra = {
            k: current.get(k)
            for k in ("company_name", "sector", "country", "company_number", "loan_id", "seniority", "maturity")
            if k in current
        }

        rows.append(
            process_borrower_period(
                borrower_id=borrower_id,
                current=current,
                previous=previous,
                covenants=covenants,
                collateral_value=collateral_value,
                extra=extra,
            )
        )

    result_df = pd.DataFrame(rows)
    if "delta_el" in result_df.columns and result_df["delta_el"].notna().any():
        result_df = result_df.sort_values("delta_el", ascending=False, na_position="last")
    else:
        result_df = result_df.sort_values("expected_loss", ascending=False)
    return result_df.reset_index(drop=True)


def analyse_portfolio(csv_path: str) -> pd.DataFrame:
    """
    Load a portfolio CSV and return a DataFrame ranked by expected-loss
    deterioration. This is the "definition of done" function from Week 1 of
    the build plan.

    Example
    -------
    >>> df = analyse_portfolio("sample_data/demo_portfolio.csv")
    >>> df[["borrower_id", "expected_loss", "delta_el", "risk_band"]].head()
    """
    df = pd.read_csv(csv_path)
    return analyse_portfolio_df(df)

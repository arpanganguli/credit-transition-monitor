import pandas as pd

def calculate_changes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df = df.sort_values(
        ["borrower_id", "period"]
    )

    group = df.groupby("borrower_id")

    # Absolute changes
    df["delta_ebitda"] = group["ebitda"].diff()
    df["delta_revenue"] = group["revenue"].diff()
    df["delta_leverage"] = group["leverage"].diff()
    df["delta_interest_cover"] = (
        group["interest_cover"].diff()
    )

    # Percentage changes
    df["ebitda_change_pct"] = (
        group["ebitda"].pct_change()
    )

    df["revenue_change_pct"] = (
        group["revenue"].pct_change()
    )

    df["delta_leverage_change_pct"] = (
        group["leverage"].pct_change()
    )

    df["delta_interest_cover_change_pct"] = (
        group["interest_cover"].pct_change()
    )

    return df
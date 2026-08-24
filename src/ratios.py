import pandas as pd


def calculate_ratios(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["net_debt"] = df["debt"] - df["cash"]

    df["leverage"] = (
        df["debt"] / df["ebitda"]
    )

    df["net_leverage"] = (
        df["net_debt"] / df["ebitda"]
    )

    df["interest_cover"] = (
        df["ebitda"] / df["interest_expense"]
    )

    df["ebitda_margin"] = (
        df["ebitda"] / df["revenue"]
    )

    df["expected_loss"] = (
        df["ead"]
        * df["pd"]
        * df["lgd"]
    )

    return df
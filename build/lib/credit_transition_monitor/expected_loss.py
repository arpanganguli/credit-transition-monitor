import pandas as pd

def calculate_expected_loss(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["expected_loss"] = (
        df["ead"]
        * df["pd"]
        * df["lgd"]
    )

    return df
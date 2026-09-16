"""
End-to-end orchestration tests -- the Week 1 "definition of done":

    run analyse_portfolio("portfolio.csv") on a 50-borrower synthetic
    portfolio and return a DataFrame ranked by expected-loss deterioration
"""

from pathlib import Path

import pandas as pd
import pytest

from credit.portfolio import analyse_portfolio, analyse_portfolio_df

DEMO_CSV = Path(__file__).resolve().parent.parent / "sample_data" / "demo_portfolio.csv"


def test_analyse_portfolio_on_the_synthetic_50_borrower_book():
    df = analyse_portfolio(str(DEMO_CSV))
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 50
    # Ranked by expected-loss deterioration: Delta EL should be non-increasing.
    deltas = df["delta_el"].dropna().tolist()
    assert deltas == sorted(deltas, reverse=True)
    # Every borrower has a valid risk band and a non-negative expected loss.
    assert set(df["risk_band"].unique()) <= {"GREEN", "AMBER", "RED", "CRITICAL"}
    assert (df["expected_loss"] >= 0).all()


def test_analyse_portfolio_minimal_week1_csv(tmp_path):
    """The exact minimal single-period CSV shape from the Week 1 example."""
    csv_path = tmp_path / "portfolio.csv"
    csv_path.write_text(
        "borrower,EAD,PD,LGD,revenue,EBITDA,debt,cash,interest\n"
        "ABC Ltd,18000000,0.06,0.45,50000000,8000000,35000000,4000000,5000000\n"
    )
    df = analyse_portfolio(str(csv_path))
    assert len(df) == 1
    row = df.iloc[0]
    assert row["borrower_id"] == "ABC Ltd"
    assert row["expected_loss"] == pytest.approx(486_000)
    # No previous period in this file, so there is nothing to attribute yet.
    assert row["delta_el"] is None


def test_analyse_portfolio_missing_required_column_raises():
    bad_df = pd.DataFrame([{"borrower_id": "X", "ead": 1_000_000}])
    with pytest.raises(ValueError):
        analyse_portfolio_df(bad_df)


def test_flagship_borrower_is_flagged_and_reproducible():
    df = analyse_portfolio(str(DEMO_CSV)).set_index("borrower_id")
    abc = df.loc["BRW-001"]
    assert abc["risk_band"] in {"RED", "CRITICAL"}
    assert abc["score"] > 0
    assert len(abc["reasons"]) > 0
    # Re-running must give exactly the same answer -- the whole point of the product.
    df2 = analyse_portfolio(str(DEMO_CSV)).set_index("borrower_id")
    assert df2.loc["BRW-001", "expected_loss"] == abc["expected_loss"]
    assert df2.loc["BRW-001", "score"] == abc["score"]

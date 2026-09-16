from pathlib import Path
import pandas as pd
import pytest
@pytest.fixture
def demo():
    return pd.read_csv(Path(__file__).resolve().parents[1]/"sample_data/demo_portfolio.csv")
@pytest.fixture
def simple():
    return pd.DataFrame([dict(borrower_id="A",company_name="Example",currency="GBP",period=p,ead=1000.0,baseline_pd=.06,baseline_lgd=.45,revenue=1000.0,ebitda=200.0,debt=600.0,cash=200,interest_expense=50,max_leverage=5,min_interest_cover=1.5,min_liquidity=50,collateral_value=800) for p in ["2026-03-31","2026-06-30"]])

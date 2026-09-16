"""Deterministic fictional borrowers; no external company data."""
from pathlib import Path
import numpy as np
import pandas as pd

def generate():
    rng = np.random.default_rng(42)
    rows=[]
    sectors=["Industrials","Healthcare","Business services","Consumer","Logistics"]
    names=["Alder Logistics", "Beacon Foods", "Cedar Manufacturing", "Dale Healthcare", "Elm Services"]
    for i in range(50):
        revenue=rng.uniform(25,100)*1e6
        ebitda=revenue*rng.uniform(.13,.25)
        debt=ebitda*rng.uniform(2,4)
        cash=debt*.16
        category=i%5
        growth=[-.16,-.08,-.03,.015,.04][category]
        for t,period in enumerate(["2025-09-30","2025-12-31","2026-03-31","2026-06-30"]):
            rows.append(dict(borrower_id=f"B{i+1:03}",company_name=names[i] if i<5 else f"{['North','West','Oak','Brook','Vale'][i%5]} {['Engineering','Care','Partners','Foods','Freight'][i%5]} {i+1:02}",sector=sectors[i%5],country="GB",currency="GBP",period=period,ead=debt*.7*(1+.02*t),baseline_pd=.025+.005*category+.002*t,baseline_lgd=.35+.02*category+.008*t,revenue=revenue*(1+growth*.7)**t,ebitda=ebitda*(1+growth)**t,debt=debt*(1+(.035 if category<2 else -.025))**t,cash=cash*(1+growth*1.8)**t,interest_expense=debt*.08*(1+.05*t),max_leverage=4.5,min_interest_cover=1.5,min_liquidity=cash*.5,collateral_value=debt*.85,assets=debt*1.3))
    d=pd.DataFrame(rows)
    for c in d.select_dtypes('number'): d[c]=d[c].round(6)
    return d
if __name__ == "__main__":
    root=Path(__file__).parent
    generate().to_csv(root/"demo_portfolio.csv",index=False)

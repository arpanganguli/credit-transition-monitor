import numpy as np

def calculate_ratios(df):
    d = df.copy()
    d["net_debt"] = d.debt - d.cash
    # Undefined/non-economic leverage is never represented as a healthy negative ratio.
    d["leverage"] = (d.debt / d.ebitda.where(d.ebitda > 0)).replace([np.inf, -np.inf], np.nan)
    d["net_leverage"] = d.net_debt / d.ebitda.where(d.ebitda > 0)
    d["interest_cover"] = d.ebitda / d.interest_expense.where(d.interest_expense > 0)
    d["ebitda_margin"] = d.ebitda / d.revenue.where(d.revenue > 0)
    d["nonpositive_ebitda"] = d.ebitda <= 0
    return d

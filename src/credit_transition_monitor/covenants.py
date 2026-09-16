import numpy as np

def calculate_covenants(df):
    d = df.copy()
    d["leverage_headroom"] = (d.max_leverage - d.leverage) / d.max_leverage
    d.loc[d.nonpositive_ebitda, "leverage_headroom"] = -1.0
    d["interest_headroom"] = (d.interest_cover - d.min_interest_cover) / d.min_interest_cover
    d["liquidity_headroom"] = (d.cash - d.min_liquidity) / d.min_liquidity.where(d.min_liquidity > 0)
    d["covenant_headroom"] = d[["leverage_headroom", "interest_headroom", "liquidity_headroom"]].min(axis=1)
    d["leverage_breach"] = (d.leverage > d.max_leverage) | d.nonpositive_ebitda
    d["interest_breach"] = d.interest_cover < d.min_interest_cover
    d["liquidity_breach"] = d.cash < d.min_liquidity
    d["covenant_breach"] = d[["leverage_breach", "interest_breach", "liquidity_breach"]].any(axis=1)
    return d

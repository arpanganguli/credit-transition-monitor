import numpy as np

RULES = [
    ("ebitda", "EBITDA decline", "10–20%: 8; >20%: 15", 15),
    ("leverage_change", "Leverage increase", ">1.0x", 15),
    ("leverage_covenant", "Leverage covenant", "Above limit", 20),
    ("interest_cover", "Interest cover", "<1.5x: 15; <1.0x: 20", 20),
    ("headroom", "Minimum covenant headroom", "<10%", 15),
    ("breach", "Any covenant breach", "One or more breaches", 25),
    ("cash", "Cash decline", ">25%", 10),
    ("revenue", "Revenue decline", ">15%", 8),
]
MULTIPLIERS = {"GREEN": 1.0, "AMBER": 1.5, "RED": 2.5, "CRITICAL": 4.0}

def risk_band(score):
    return "GREEN" if score < 25 else "AMBER" if score < 50 else "RED" if score < 75 else "CRITICAL"

def calculate_risk_score(df):
    d = df.copy()
    d["points_ebitda"] = np.select([d.ebitda_change_pct < -0.20, d.ebitda_change_pct <= -0.10], [15, 8], default=0)
    d["points_leverage_change"] = (d.delta_leverage > 1.0).astype(int) * 15
    d["points_leverage_covenant"] = d.leverage_breach.astype(int) * 20
    d["points_interest_cover"] = np.select([d.interest_cover < 1.0, d.interest_cover < 1.5], [20, 15], default=0)
    d["points_headroom"] = (d.covenant_headroom < .10).astype(int) * 15
    d["points_breach"] = d.covenant_breach.astype(int) * 25
    d["points_cash"] = (d.cash_change_pct < -.25).astype(int) * 10
    d["points_revenue"] = (d.revenue_change_pct < -.15).astype(int) * 8
    d["raw_score"] = d[["points_"+r[0] for r in RULES]].sum(axis=1)
    d["risk_score"] = d.raw_score.clip(upper=100)
    d["cap_adjustment"] = d.risk_score - d.raw_score
    d["risk_band"] = d.risk_score.map(risk_band)
    d["pd_multiplier"] = d.risk_band.map(MULTIPLIERS)
    return d

def explain(row):
    import pandas as pd
    values = [row.ebitda_change_pct, row.delta_leverage, row.leverage, row.interest_cover, row.covenant_headroom, row.covenant_breach, row.cash_change_pct, row.revenue_change_pct]
    def show(i,v):
        if pd.isna(v):
            return "Undefined; assumed breach" if i == 2 and row.nonpositive_ebitda else "Unavailable (no points)"
        if i == 5: return "Yes" if v else "No"
        if i in (0,4,6,7): return f"{v:.1%}"
        return f"{v:.2f}x"
    return pd.DataFrame([{"Signal": label, "Observed": show(i,values[i]), "Rule": rule, "Points": int(row["points_"+key])} for i,(key,label,rule,_) in enumerate(RULES)])

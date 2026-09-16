def calculate_changes(df):
    d = df.sort_values(["borrower_id", "period"]).copy()
    g = d.groupby("borrower_id", sort=False)
    for c in ["ebitda", "revenue", "leverage", "interest_cover", "cash"]:
        d["delta_" + c] = g[c].diff()
    for c in ["ebitda", "revenue", "cash"]:
        previous = g[c].shift()
        d[c + "_change_pct"] = (d[c] - previous) / previous.where(previous > 0)
    d["has_previous"] = g.cumcount() > 0
    return d

def calculate_expected_loss(df):
    d = df.copy()
    d["expected_loss"] = d.ead * d.pd * d.lgd
    return d

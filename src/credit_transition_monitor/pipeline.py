from pathlib import Path
import numpy as np
from .validation import read_portfolio, validate_portfolio
from .ratios import calculate_ratios
from .changes import calculate_changes
from .covenants import calculate_covenants
from .early_warning import calculate_risk_score
from .pd_overlay import calculate_stressed_pd
from .expected_loss import calculate_expected_loss
from .attribution import shapley_el

def analyse_portfolio(source):
    d = read_portfolio(source) if isinstance(source, (str, Path)) else source
    d = validate_portfolio(d)
    for function in [calculate_ratios, calculate_changes, calculate_covenants, calculate_risk_score]:
        d = function(d)
    d["pd"] = calculate_stressed_pd(d.baseline_pd, d.pd_multiplier)
    d["lgd"] = d.baseline_lgd
    d["baseline_el"] = d.ead * d.baseline_pd * d.baseline_lgd
    d = calculate_expected_loss(d)
    d["delta_el"] = d.groupby("borrower_id").expected_loss.diff()
    for c in ["ead", "pd", "lgd"]:
        d["attribution_"+c] = np.nan
    for _, group in d.groupby("borrower_id"):
        for k in range(1,len(group)):
            previous, current = group.iloc[k-1], group.iloc[k]
            result = shapley_el(previous[["ead","pd","lgd"]], current[["ead","pd","lgd"]])
            for c,v in result.items():
                d.loc[current.name, "attribution_"+c] = v
    return d

def rank_borrowers(results):
    return results.sort_values("period").groupby("borrower_id", as_index=False).tail(1).sort_values(["delta_el", "risk_score", "expected_loss"], ascending=False, na_position="last").reset_index(drop=True)

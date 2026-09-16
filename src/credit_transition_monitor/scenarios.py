from dataclasses import dataclass, asdict
import numpy as np
from .pipeline import analyse_portfolio, rank_borrowers
from .attribution import shapley_el

@dataclass(frozen=True)
class Scenario:
    ebitda_pct: float = 0.0
    revenue_pct: float = 0.0
    collateral_pct: float = 0.0
    interest_bps: float = 0.0
    def __post_init__(self):
        for key, value in asdict(self).items():
            low, high = (-1000,1000) if key == "interest_bps" else (-1,1)
            if not np.isfinite(value) or not low <= value <= high:
                raise ValueError(f"{key} must be within [{low}, {high}]")
        if self.revenue_pct <= -1:
            raise ValueError("Revenue shock must be greater than -100%")

def stress_portfolio(raw, scenario):
    history = analyse_portfolio(raw)
    baseline = rank_borrowers(history).set_index("borrower_id")
    d = raw.copy()
    # Validation/sorting also canonicalises aliases and dates before applying shocks.
    from .validation import validate_portfolio
    d = validate_portfolio(d)
    latest = d.period.eq(d.period.max())
    d.loc[latest, "ebitda"] *= 1 + scenario.ebitda_pct
    d.loc[latest, "revenue"] *= 1 + scenario.revenue_pct
    d.loc[latest, "interest_expense"] = (d.loc[latest, "interest_expense"] + d.loc[latest, "debt"] * scenario.interest_bps / 10000).clip(lower=1e-8)
    d.loc[latest, "collateral_value"] *= 1 + scenario.collateral_pct
    result = rank_borrowers(analyse_portfolio(d)).set_index("borrower_id").reindex(baseline.index)
    # Assumption: all baseline recovery is collateral-sensitive. EAD-independent,
    # bounded and identity at zero shock; collateral coverage is NOT inferred.
    result["lgd"] = baseline.lgd.copy() if scenario.collateral_pct == 0 else (1 - (1 - baseline.lgd) * (1 + scenario.collateral_pct)).clip(0,1)
    result["expected_loss"] = result.ead * result.pd * result.lgd
    result["current_el"] = baseline.expected_loss
    result["scenario_delta_el"] = result.expected_loss - baseline.expected_loss
    for bid,row in result.iterrows():
        prior = history[(history.borrower_id == bid) & (history.period < row.period)]
        if not prior.empty:
            previous = prior.iloc[-1]
            result.loc[bid, "delta_el"] = row.expected_loss - previous.expected_loss
            for c,v in shapley_el(previous[["ead","pd","lgd"]], row[["ead","pd","lgd"]]).items():
                result.loc[bid, "attribution_"+c] = v
        parts = shapley_el(baseline.loc[bid,["ead","pd","lgd"]], row[["ead","pd","lgd"]])
        for c,v in parts.items():
            result.loc[bid,"scenario_attribution_"+c] = v
    return result.reset_index()

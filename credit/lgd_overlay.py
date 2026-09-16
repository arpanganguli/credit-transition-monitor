"""
LGD overlay: adjust a lender-supplied baseline LGD for risk-band severity and
collateral coverage.

Two effects are modelled, both clearly labelled as prototype assumptions:

1. Distressed-recovery uplift. As a borrower migrates to a worse risk band,
   recoveries in a real workout tend to be lower (rushed disposals, weaker
   negotiating position), so we apply a small multiplicative uplift to LGD by
   band.

2. Collateral credit. Collateral covering the exposure reduces loss given
   default. Coverage is deliberately computed against the loan's *on-record*
   EAD (the exposure table's baseline EAD), not against a hypothetical
   stress-scenario EAD -- collateral coverage is a structural feature of the
   loan, not something that should silently move just because a stress test
   is exploring a bigger drawn balance. This keeps "shock EAD" and "shock
   collateral" independent and testable (see tests/test_lgd.py and
   tests/test_scenarios.py).
"""

from __future__ import annotations

from typing import Optional

from credit.early_warning import RiskBand

# Modest distressed-recovery uplift by band. 1.00 = no adjustment.
LGD_BAND_MULTIPLIERS: dict[RiskBand, float] = {
    RiskBand.GREEN: 1.00,
    RiskBand.AMBER: 1.05,
    RiskBand.RED: 1.15,
    RiskBand.CRITICAL: 1.30,
}

# Maximum LGD reduction (in LGD points) available from full collateral coverage.
MAX_COLLATERAL_CREDIT = 0.20

LGD_FLOOR = 0.01
LGD_CEILING = 1.00


def lgd_band_multiplier(band: RiskBand) -> float:
    try:
        return LGD_BAND_MULTIPLIERS[band]
    except KeyError as exc:
        raise ValueError(f"Unknown risk band: {band!r}") from exc


def collateral_coverage_ratio(
    collateral_value: Optional[float], ead_baseline: Optional[float]
) -> float:
    """
    Collateral value as a fraction of the loan's on-record EAD, capped at 1.0
    (over-collateralisation does not earn extra LGD credit beyond full cover).
    """
    if not collateral_value or not ead_baseline or ead_baseline <= 0:
        return 0.0
    return max(0.0, min(1.0, collateral_value / ead_baseline))


def stressed_lgd(
    baseline_lgd: float,
    band: RiskBand,
    collateral_value: Optional[float] = None,
    ead_baseline: Optional[float] = None,
    max_collateral_credit: float = MAX_COLLATERAL_CREDIT,
) -> float:
    """
    Compute the indicative stressed LGD.

        LGD* = clamp(baseline_LGD x band_multiplier - collateral_credit)

    where collateral_credit = coverage_ratio x max_collateral_credit.
    """
    if baseline_lgd is None:
        raise ValueError("baseline_lgd is required")
    coverage = collateral_coverage_ratio(collateral_value, ead_baseline)
    credit = coverage * max_collateral_credit
    lgd = baseline_lgd * lgd_band_multiplier(band) - credit
    return max(LGD_FLOOR, min(LGD_CEILING, lgd))

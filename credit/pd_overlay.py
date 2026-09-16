"""
PD overlay: turn a lender-supplied baseline PD into an indicative stressed PD.

This uses a hazard-rate transformation rather than simply multiplying the
probability (which breaks down and can exceed 100% as PD rises):

    lambda   = -ln(1 - PD0)
    lambda*  = m * lambda
    PD*      = 1 - e^(-lambda*)

where ``m`` is a risk-band multiplier. This behaves sensibly across the full
[0, 1) range and always returns a valid probability.

IMPORTANT: this is a product heuristic to make deterioration visible and
explainable in a prototype. It is explicitly NOT a validated regulatory PD
model, and multipliers below are prototype assumptions to test with users.
"""

from __future__ import annotations

import math
from typing import Optional

from credit.early_warning import RiskBand

# Risk-band multipliers, as specified in the build plan (Week 2).
BAND_MULTIPLIERS: dict[RiskBand, float] = {
    RiskBand.GREEN: 1.0,
    RiskBand.AMBER: 1.5,
    RiskBand.RED: 2.5,
    RiskBand.CRITICAL: 4.0,
}


def hazard_rate(pd0: float) -> float:
    """lambda = -ln(1 - PD0). Raises ValueError if pd0 is not in [0, 1)."""
    if pd0 is None:
        raise ValueError("pd0 is required")
    if not (0.0 <= pd0 < 1.0):
        raise ValueError(f"pd0 must be in [0, 1), got {pd0}")
    return -math.log(1.0 - pd0)


def stressed_pd(pd0: float, multiplier: float) -> float:
    """
    Apply the hazard-rate transform with an explicit multiplier.

    This is the generic, testable primitive. ``stressed_pd_from_band`` below
    is the convenience wrapper that derives the multiplier from a risk band.
    """
    if multiplier is None or multiplier < 0:
        raise ValueError(f"multiplier must be >= 0, got {multiplier}")
    lam = hazard_rate(pd0)
    lam_star = multiplier * lam
    pd_star = 1.0 - math.exp(-lam_star)
    return pd_star


def band_multiplier(band: RiskBand) -> float:
    """Look up the prototype risk-band multiplier."""
    try:
        return BAND_MULTIPLIERS[band]
    except KeyError as exc:
        raise ValueError(f"Unknown risk band: {band!r}") from exc


def stressed_pd_from_band(pd0: float, band: RiskBand) -> float:
    """Convenience: derive the multiplier from the borrower's current risk band."""
    return stressed_pd(pd0, band_multiplier(band))


def implied_multiplier(pd0: float, pd_star: float) -> Optional[float]:
    """
    Inverse of stressed_pd: recover the multiplier implied by an observed
    (pd0, pd*) pair. Useful for validation/debugging. Returns None if pd0 is 0
    (no hazard rate to scale).
    """
    lam = hazard_rate(pd0)
    if lam == 0:
        return None
    lam_star = -math.log(1.0 - pd_star)
    return lam_star / lam

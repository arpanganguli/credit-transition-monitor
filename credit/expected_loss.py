"""
Expected loss: the core equation the whole product is built around.

    EL = EAD x PD x LGD

Track both the amount and the movement: Delta EL = EL(t) - EL(t-1).
"""

from __future__ import annotations

from typing import Optional


def expected_loss(ead: float, pd: float, lgd: float) -> float:
    """EL = EAD x PD x LGD."""
    if ead is None or pd is None or lgd is None:
        raise ValueError("ead, pd and lgd are all required")
    return ead * pd * lgd


def delta_expected_loss(el_current: float, el_previous: Optional[float]) -> Optional[float]:
    """Delta EL = EL(t) - EL(t-1). None if there is no previous period."""
    if el_previous is None:
        return None
    return el_current - el_previous


def delta_expected_loss_pct(el_current: float, el_previous: Optional[float]) -> Optional[float]:
    """Percentage movement in EL, None if there is no previous period or it was zero."""
    if el_previous is None or el_previous == 0:
        return None
    return (el_current - el_previous) / abs(el_previous)

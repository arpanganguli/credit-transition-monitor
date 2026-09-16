"""
The early-warning scorecard: an explainable, capped-at-100 risk score.

Deliberately NOT a trained ML model (Week 2 of the build plan is explicit
about this). Every point on the scorecard traces back to one condition on one
observable metric, so a credit analyst can always answer "why is this
borrower flagged?" without hand-waving about a black box.

Scoring rule
------------
The signal table groups conditions into six families (EBITDA, Leverage,
Interest cover, Covenant, Cash, Revenue). Within a family, only the single
highest-scoring condition that is met contributes -- conditions are tiers of
severity on the same underlying metric, not independent add-ons. The score is
the sum across families, capped at 100.

    EBITDA          decline >20%              +15
                    decline 10-20%            +8
    Leverage        increase >1x              +15
                    above covenant            +20
    Interest cover  <1.5x                     +15
                    <1.0x                     +20
    Covenant        headroom <10%             +15
                    breach                    +25
    Cash            decline >25%              +10
    Revenue         decline >15%              +8

Risk bands
----------
    0-24    GREEN
    25-49   AMBER
    50-74   RED
    75-100  CRITICAL

These thresholds and point values are product assumptions to test with
users, not statistically calibrated probabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RiskBand(str, Enum):
    GREEN = "GREEN"
    AMBER = "AMBER"
    RED = "RED"
    CRITICAL = "CRITICAL"


BAND_ORDER = [RiskBand.GREEN, RiskBand.AMBER, RiskBand.RED, RiskBand.CRITICAL]

BAND_RANGES: dict[RiskBand, tuple[int, int]] = {
    RiskBand.GREEN: (0, 24),
    RiskBand.AMBER: (25, 49),
    RiskBand.RED: (50, 74),
    RiskBand.CRITICAL: (75, 100),
}


def score_to_band(score: float) -> RiskBand:
    """Map a 0-100 score to its risk band."""
    score = max(0, min(100, score))
    for band, (low, high) in BAND_RANGES.items():
        if low <= score <= high:
            return band
    return RiskBand.CRITICAL  # unreachable given the ranges above, but safe


@dataclass
class ScoreReason:
    """One line of the Risk Drivers explanation: a family, its trigger, and points."""

    family: str
    label: str
    points: int
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "family": self.family,
            "label": self.label,
            "points": self.points,
            "detail": self.detail,
        }


@dataclass
class ScorecardResult:
    """Full scorecard output: total score, band, and the reasons behind it."""

    score: int
    band: RiskBand
    reasons: list[ScoreReason] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "band": self.band.value,
            "reasons": [r.to_dict() for r in self.reasons],
        }

    def narrative(self) -> str:
        """A one-paragraph, human-readable explanation of the score."""
        if not self.reasons:
            return "No deterioration signals triggered. Score 0 (GREEN)."
        parts = [f"{r.label} ({r.points:+d})" for r in self.reasons]
        return f"Score {self.score} ({self.band.value}): " + "; ".join(parts) + "."


def _fmt_pct(x: Optional[float]) -> str:
    if x is None:
        return "n/a"
    return f"{x * 100:.0f}%"


def score_ebitda(ebitda_change: Optional[float]) -> Optional[ScoreReason]:
    """EBITDA decline tiers. ebitda_change is a fraction, e.g. -0.24 for -24%."""
    if ebitda_change is None or ebitda_change >= 0:
        return None
    decline = -ebitda_change
    if decline > 0.20:
        return ScoreReason(
            "ebitda", "EBITDA declined >20%", 15, f"EBITDA change {_fmt_pct(ebitda_change)}"
        )
    if decline >= 0.10:
        return ScoreReason(
            "ebitda", "EBITDA declined 10-20%", 8, f"EBITDA change {_fmt_pct(ebitda_change)}"
        )
    return None


def score_leverage(
    leverage_change: Optional[float],
    leverage_current: Optional[float],
    max_leverage: Optional[float],
) -> Optional[ScoreReason]:
    """Leverage tiers: increase >1x, or breach of the max-leverage covenant."""
    candidates: list[ScoreReason] = []
    if leverage_change is not None and leverage_change > 1.0:
        candidates.append(
            ScoreReason(
                "leverage",
                "Leverage increased >1.0x",
                15,
                f"Leverage change +{leverage_change:.2f}x",
            )
        )
    if (
        leverage_current is not None
        and max_leverage is not None
        and leverage_current > max_leverage
    ):
        candidates.append(
            ScoreReason(
                "leverage",
                "Leverage covenant breached",
                20,
                f"Leverage {leverage_current:.2f}x vs covenant {max_leverage:.2f}x",
            )
        )
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.points)


def score_interest_cover(interest_cover_current: Optional[float]) -> Optional[ScoreReason]:
    """Interest cover tiers: <1.5x, or the more severe <1.0x."""
    if interest_cover_current is None:
        return None
    if interest_cover_current < 1.0:
        return ScoreReason(
            "interest_cover",
            "Interest cover below 1.0x",
            20,
            f"Interest cover {interest_cover_current:.2f}x",
        )
    if interest_cover_current < 1.5:
        return ScoreReason(
            "interest_cover",
            "Interest cover below 1.5x",
            15,
            f"Interest cover {interest_cover_current:.2f}x",
        )
    return None


def score_covenant(
    headroom: Optional[float],
    breached: bool,
) -> Optional[ScoreReason]:
    """
    Covenant tiers: headroom <10% (amber warning), or an outright breach.

    ``headroom`` is the smallest fractional headroom across all covenants
    attached to the loan (see scenarios.covenant_headroom). ``breached`` is
    True if any covenant is currently breached.
    """
    candidates: list[ScoreReason] = []
    if headroom is not None and headroom < 0.10 and not breached:
        candidates.append(
            ScoreReason(
                "covenant",
                "Covenant headroom below 10%",
                15,
                f"Headroom {_fmt_pct(headroom)}",
            )
        )
    if breached:
        candidates.append(ScoreReason("covenant", "Covenant breached", 25, "One or more covenants breached"))
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.points)


def score_cash(cash_change: Optional[float]) -> Optional[ScoreReason]:
    """Cash decline >25%."""
    if cash_change is None or cash_change >= 0:
        return None
    if -cash_change > 0.25:
        return ScoreReason("cash", "Cash declined >25%", 10, f"Cash change {_fmt_pct(cash_change)}")
    return None


def score_revenue(revenue_change: Optional[float]) -> Optional[ScoreReason]:
    """Revenue decline >15%."""
    if revenue_change is None or revenue_change >= 0:
        return None
    if -revenue_change > 0.15:
        return ScoreReason(
            "revenue", "Revenue declined >15%", 8, f"Revenue change {_fmt_pct(revenue_change)}"
        )
    return None


def compute_scorecard(
    ebitda_change: Optional[float],
    leverage_change: Optional[float],
    leverage_current: Optional[float],
    max_leverage: Optional[float],
    interest_cover_current: Optional[float],
    covenant_headroom: Optional[float],
    covenant_breached: bool,
    cash_change: Optional[float],
    revenue_change: Optional[float],
) -> ScorecardResult:
    """Run every family's scoring rule and combine into a capped-at-100 result."""
    reasons = [
        score_ebitda(ebitda_change),
        score_leverage(leverage_change, leverage_current, max_leverage),
        score_interest_cover(interest_cover_current),
        score_covenant(covenant_headroom, covenant_breached),
        score_cash(cash_change),
        score_revenue(revenue_change),
    ]
    reasons = [r for r in reasons if r is not None]
    total = min(100, sum(r.points for r in reasons))
    # Order reasons by points descending so the biggest drivers show first.
    reasons.sort(key=lambda r: r.points, reverse=True)
    return ScorecardResult(score=total, band=score_to_band(total), reasons=reasons)

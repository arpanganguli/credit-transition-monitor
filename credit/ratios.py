"""
Borrower-level financial ratio calculations.

These are the "minimum calculations" from the build plan (Week 1):

    Net debt        = Debt - Cash
    Leverage        = Debt / EBITDA
    Net leverage    = (Debt - Cash) / EBITDA
    Interest cover  = EBITDA / Interest expense
    EBITDA margin   = EBITDA / Revenue
    Expected loss   = EAD x PD x LGD   (see expected_loss.py)

All functions guard against division by zero and return ``None`` (not an
exception, not inf/nan) when a ratio is undefined, so downstream code and the
UI can display "n/a" instead of crashing or silently producing garbage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


def _safe_div(numerator: float, denominator: float) -> Optional[float]:
    """Division that returns None instead of raising or returning inf/nan."""
    if denominator is None or numerator is None:
        return None
    try:
        if denominator == 0:
            return None
        result = numerator / denominator
    except (TypeError, ZeroDivisionError):
        return None
    return result


def net_debt(debt: float, cash: float) -> Optional[float]:
    """Net debt = Debt - Cash."""
    if debt is None or cash is None:
        return None
    return debt - cash


def leverage(debt: float, ebitda: float) -> Optional[float]:
    """Leverage = Debt / EBITDA."""
    return _safe_div(debt, ebitda)


def net_leverage(debt: float, cash: float, ebitda: float) -> Optional[float]:
    """Net leverage = (Debt - Cash) / EBITDA."""
    nd = net_debt(debt, cash)
    return _safe_div(nd, ebitda)


def interest_cover(ebitda: float, interest_expense: float) -> Optional[float]:
    """Interest cover = EBITDA / Interest expense."""
    return _safe_div(ebitda, interest_expense)


def ebitda_margin(ebitda: float, revenue: float) -> Optional[float]:
    """EBITDA margin = EBITDA / Revenue."""
    return _safe_div(ebitda, revenue)


@dataclass
class BorrowerRatios:
    """The full set of computed ratios for a single borrower-period."""

    net_debt: Optional[float]
    leverage: Optional[float]
    net_leverage: Optional[float]
    interest_cover: Optional[float]
    ebitda_margin: Optional[float]

    def to_dict(self) -> dict:
        return {
            "net_debt": self.net_debt,
            "leverage": self.leverage,
            "net_leverage": self.net_leverage,
            "interest_cover": self.interest_cover,
            "ebitda_margin": self.ebitda_margin,
        }


def compute_ratios(
    revenue: float,
    ebitda: float,
    debt: float,
    cash: float,
    interest_expense: float,
) -> BorrowerRatios:
    """Compute the full minimum-calculations ratio set for one borrower-period."""
    return BorrowerRatios(
        net_debt=net_debt(debt, cash),
        leverage=leverage(debt, ebitda),
        net_leverage=net_leverage(debt, cash, ebitda),
        interest_cover=interest_cover(ebitda, interest_expense),
        ebitda_margin=ebitda_margin(ebitda, revenue),
    )


def pct_change(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    """
    Period-on-period percentage change: (current - previous) / |previous|.

    Returns None when previous is missing, zero, or either value is missing.
    A positive value means the metric increased; for metrics where a decline
    is the risk signal (EBITDA, revenue, cash), callers should treat a
    *negative* pct_change as deterioration.
    """
    if current is None or previous is None:
        return None
    if previous == 0:
        return None
    return (current - previous) / abs(previous)


@dataclass
class PeriodChanges:
    """Period-on-period changes used to drive the early-warning scorecard."""

    ebitda_change: Optional[float]
    revenue_change: Optional[float]
    cash_change: Optional[float]
    leverage_change: Optional[float]  # absolute change in turns (x), not a %
    interest_cover_current: Optional[float]

    def to_dict(self) -> dict:
        return {
            "ebitda_change": self.ebitda_change,
            "revenue_change": self.revenue_change,
            "cash_change": self.cash_change,
            "leverage_change": self.leverage_change,
            "interest_cover_current": self.interest_cover_current,
        }


def compute_period_changes(
    current: dict,
    previous: Optional[dict],
) -> PeriodChanges:
    """
    Compute the period-on-period changes needed by the early-warning scorecard.

    ``current`` and ``previous`` are dicts with keys: revenue, ebitda, debt,
    cash, interest_expense. ``previous`` may be None (first reporting period),
    in which case all changes are None (no deterioration can be measured yet).
    """
    if previous is None:
        curr_ratios = compute_ratios(**current)
        return PeriodChanges(
            ebitda_change=None,
            revenue_change=None,
            cash_change=None,
            leverage_change=None,
            interest_cover_current=curr_ratios.interest_cover,
        )

    curr_ratios = compute_ratios(**current)
    prev_ratios = compute_ratios(**previous)

    leverage_change = None
    if curr_ratios.leverage is not None and prev_ratios.leverage is not None:
        leverage_change = curr_ratios.leverage - prev_ratios.leverage

    return PeriodChanges(
        ebitda_change=pct_change(current.get("ebitda"), previous.get("ebitda")),
        revenue_change=pct_change(current.get("revenue"), previous.get("revenue")),
        cash_change=pct_change(current.get("cash"), previous.get("cash")),
        leverage_change=leverage_change,
        interest_cover_current=curr_ratios.interest_cover,
    )

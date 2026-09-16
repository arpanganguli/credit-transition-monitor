"""
Stress testing: apply shocks to a borrower or portfolio and recompute EL.

Five independent shocks are supported, matching the Week 4 dashboard spec
(EBITDA, revenue, collateral, interest-rate) plus an explicit EAD/drawn-amount
shock used in the Week 6 validation test cases:

    ebitda_shock_pct     e.g. -0.25 for a 25% EBITDA cut
    revenue_shock_pct    e.g. -0.10 for a 10% revenue cut
    collateral_shock_pct e.g. -0.30 for a 30% collateral value cut
    rate_shock_bps       e.g. +200 for a 200bp increase in cost of debt
    ead_shock_pct        e.g. +0.10 for a 10% increase in drawn exposure

Design note -- why an EAD shock does not move LGD
---------------------------------------------------
Collateral coverage (see lgd_overlay.collateral_coverage_ratio) is computed
against the loan's *on-record* EAD, not the shocked EAD used to recompute EL.
This is a deliberate modelling choice, not an oversight: collateral coverage
is a structural/legal feature of the loan that does not change just because
a what-if scenario explores a larger drawn balance. It is also what makes the
required regression property hold: shocking EAD alone changes EL (via the EAD
term) without perturbing PD or LGD. See tests/test_scenarios.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from credit import ratios as ratios_mod
from credit.early_warning import compute_scorecard
from credit.expected_loss import expected_loss
from credit.lgd_overlay import stressed_lgd
from credit.pd_overlay import stressed_pd_from_band


@dataclass
class Shock:
    """A bundle of stress parameters. All default to "no shock"."""

    ebitda_shock_pct: float = 0.0
    revenue_shock_pct: float = 0.0
    collateral_shock_pct: float = 0.0
    rate_shock_bps: float = 0.0
    ead_shock_pct: float = 0.0

    def is_noop(self) -> bool:
        return (
            self.ebitda_shock_pct == 0.0
            and self.revenue_shock_pct == 0.0
            and self.collateral_shock_pct == 0.0
            and self.rate_shock_bps == 0.0
            and self.ead_shock_pct == 0.0
        )

    def label(self) -> str:
        parts = []
        if self.ebitda_shock_pct:
            parts.append(f"EBITDA {self.ebitda_shock_pct:+.0%}")
        if self.revenue_shock_pct:
            parts.append(f"Revenue {self.revenue_shock_pct:+.0%}")
        if self.collateral_shock_pct:
            parts.append(f"Collateral {self.collateral_shock_pct:+.0%}")
        if self.rate_shock_bps:
            parts.append(f"Rates {self.rate_shock_bps:+.0f}bp")
        if self.ead_shock_pct:
            parts.append(f"EAD {self.ead_shock_pct:+.0%}")
        return ", ".join(parts) if parts else "No shock (baseline)"


@dataclass
class StressedBorrowerResult:
    borrower_id: str
    ead_stressed: float
    ebitda_stressed: float
    revenue_stressed: float
    debt: float
    cash: float
    interest_expense_stressed: float
    collateral_value_stressed: float
    leverage: Optional[float]
    interest_cover: Optional[float]
    score: int
    band: str
    reasons: list
    pd_stressed: float
    lgd_stressed: float
    expected_loss_stressed: float

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["reasons"] = [r.to_dict() for r in self.reasons]
        return d


def apply_shock_to_borrower(
    borrower_id: str,
    baseline_pd: float,
    baseline_lgd: float,
    ead: float,
    revenue: float,
    ebitda: float,
    debt: float,
    cash: float,
    interest_expense: float,
    max_leverage: Optional[float],
    min_interest_cover: Optional[float],
    min_liquidity: Optional[float],
    collateral_value: Optional[float],
    previous_ebitda: Optional[float] = None,
    previous_revenue: Optional[float] = None,
    previous_cash: Optional[float] = None,
    previous_leverage: Optional[float] = None,
    shock: Optional[Shock] = None,
) -> StressedBorrowerResult:
    """
    Apply a Shock to one borrower's latest reported financials and recompute
    everything downstream: ratios, scorecard, stressed PD/LGD, and EL.

    ``ead`` and ``collateral_value`` used for the *coverage ratio* are always
    the on-record (unshocked) values -- see the module docstring. The shocked
    EAD is used only in the final EL multiplication.
    """
    shock = shock or Shock()

    ebitda_s = ebitda * (1 + shock.ebitda_shock_pct)
    revenue_s = revenue * (1 + shock.revenue_shock_pct)
    collateral_s = (collateral_value or 0.0) * (1 + shock.collateral_shock_pct)
    # A rate shock raises the cost of servicing existing debt.
    interest_s = interest_expense + debt * (shock.rate_shock_bps / 10000.0)
    ead_s = ead * (1 + shock.ead_shock_pct)

    leverage_s = ratios_mod.leverage(debt, ebitda_s)
    interest_cover_s = ratios_mod.interest_cover(ebitda_s, interest_s)

    ebitda_change = ratios_mod.pct_change(ebitda_s, previous_ebitda) if previous_ebitda else None
    revenue_change = ratios_mod.pct_change(revenue_s, previous_revenue) if previous_revenue else None
    cash_change = ratios_mod.pct_change(cash, previous_cash) if previous_cash else None
    leverage_change = (leverage_s - previous_leverage) if (leverage_s is not None and previous_leverage is not None) else None

    breached = False
    headrooms = []
    if max_leverage and leverage_s is not None and max_leverage > 0:
        headrooms.append((max_leverage - leverage_s) / max_leverage)
        if leverage_s > max_leverage:
            breached = True
    if min_interest_cover and interest_cover_s is not None:
        if min_interest_cover > 0:
            headrooms.append((interest_cover_s - min_interest_cover) / min_interest_cover)
        if interest_cover_s < min_interest_cover:
            breached = True
    if min_liquidity and cash is not None:
        if min_liquidity > 0:
            headrooms.append((cash - min_liquidity) / min_liquidity)
        if cash < min_liquidity:
            breached = True
    headroom = min(headrooms) if headrooms else None

    scorecard = compute_scorecard(
        ebitda_change=ebitda_change,
        leverage_change=leverage_change,
        leverage_current=leverage_s,
        max_leverage=max_leverage,
        interest_cover_current=interest_cover_s,
        covenant_headroom=headroom,
        covenant_breached=breached,
        cash_change=cash_change,
        revenue_change=revenue_change,
    )

    pd_s = stressed_pd_from_band(baseline_pd, scorecard.band)
    lgd_s = stressed_lgd(
        baseline_lgd,
        scorecard.band,
        collateral_value=collateral_s if shock.collateral_shock_pct else collateral_value,
        ead_baseline=ead,  # on-record EAD, NOT ead_s -- see module docstring
    )
    el_s = expected_loss(ead_s, pd_s, lgd_s)

    return StressedBorrowerResult(
        borrower_id=borrower_id,
        ead_stressed=ead_s,
        ebitda_stressed=ebitda_s,
        revenue_stressed=revenue_s,
        debt=debt,
        cash=cash,
        interest_expense_stressed=interest_s,
        collateral_value_stressed=collateral_s,
        leverage=leverage_s,
        interest_cover=interest_cover_s,
        score=scorecard.score,
        band=scorecard.band.value,
        reasons=scorecard.reasons,
        pd_stressed=pd_s,
        lgd_stressed=lgd_s,
        expected_loss_stressed=el_s,
    )

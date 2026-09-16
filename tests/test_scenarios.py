"""
Stress-testing regression tests, taken directly from the Week 6 validation
table in the build plan:

    Test case                      Expected result
    EBITDA falls; else constant    Risk up; PD up; EL up
    Debt falls substantially       Leverage down; risk down
    Collateral collapses           PD unchanged; LGD up; EL up
    EAD increases                  PD unchanged; LGD unchanged; EL up
"""

import math

from credit.scenarios import Shock, apply_shock_to_borrower

BASE = dict(
    borrower_id="TEST-1",
    baseline_pd=0.04,
    baseline_lgd=0.40,
    ead=10_000_000,
    revenue=40_000_000,
    ebitda=6_000_000,
    debt=15_000_000,
    cash=2_000_000,
    interest_expense=1_100_000,
    max_leverage=3.5,
    min_interest_cover=1.75,
    min_liquidity=800_000,
    collateral_value=6_000_000,
    previous_ebitda=6_200_000,
    previous_revenue=41_000_000,
    previous_cash=2_100_000,
    previous_leverage=15_000_000 / 6_200_000,
)


def _baseline_result():
    return apply_shock_to_borrower(**BASE, shock=Shock())


def test_ebitda_falls_risk_up_pd_up_el_up():
    baseline = _baseline_result()
    shocked = apply_shock_to_borrower(**BASE, shock=Shock(ebitda_shock_pct=-0.30))
    assert shocked.score >= baseline.score
    assert shocked.pd_stressed > baseline.pd_stressed
    assert shocked.expected_loss_stressed > baseline.expected_loss_stressed


def test_debt_falls_leverage_down_risk_down():
    baseline = _baseline_result()
    kwargs = dict(BASE)
    kwargs["debt"] = BASE["debt"] * 0.5  # debt falls substantially
    shocked = apply_shock_to_borrower(**kwargs, shock=Shock())
    assert shocked.leverage < baseline.leverage
    assert shocked.score <= baseline.score


def test_collateral_collapses_pd_unchanged_lgd_up_el_up():
    baseline = _baseline_result()
    shocked = apply_shock_to_borrower(**BASE, shock=Shock(collateral_shock_pct=-1.0))
    assert math.isclose(shocked.pd_stressed, baseline.pd_stressed, rel_tol=1e-9)
    assert shocked.lgd_stressed > baseline.lgd_stressed
    assert shocked.expected_loss_stressed > baseline.expected_loss_stressed


def test_ead_increases_pd_unchanged_lgd_unchanged_el_up():
    baseline = _baseline_result()
    shocked = apply_shock_to_borrower(**BASE, shock=Shock(ead_shock_pct=0.25))
    assert math.isclose(shocked.pd_stressed, baseline.pd_stressed, rel_tol=1e-9)
    assert math.isclose(shocked.lgd_stressed, baseline.lgd_stressed, rel_tol=1e-9)
    assert shocked.expected_loss_stressed > baseline.expected_loss_stressed
    # And the increase should be explained purely by the EAD multiplier.
    assert math.isclose(
        shocked.expected_loss_stressed, baseline.expected_loss_stressed * 1.25, rel_tol=1e-6
    )


def test_no_shock_is_a_true_baseline():
    a = apply_shock_to_borrower(**BASE, shock=Shock())
    b = apply_shock_to_borrower(**BASE, shock=None)
    assert a.expected_loss_stressed == b.expected_loss_stressed


def test_rate_shock_reduces_interest_cover_and_can_only_raise_or_hold_risk():
    baseline = _baseline_result()
    shocked = apply_shock_to_borrower(**BASE, shock=Shock(rate_shock_bps=300))
    assert shocked.interest_cover < baseline.interest_cover
    assert shocked.score >= baseline.score

"""
Ratio calculations, checked against the Week 1 worked example from the build
plan: ABC Ltd, EAD=18,000,000 PD=0.06 LGD=0.45 revenue=50,000,000
EBITDA=8,000,000 debt=35,000,000 cash=4,000,000 interest=5,000,000, which the
plan states should give leverage=4.375, interest_cover=1.6, net_debt=31,000,000,
expected_loss=486,000.
"""

import math

from credit.ratios import (
    compute_period_changes,
    compute_ratios,
    ebitda_margin,
    interest_cover,
    leverage,
    net_debt,
    net_leverage,
    pct_change,
)

ABC = dict(revenue=50_000_000, ebitda=8_000_000, debt=35_000_000, cash=4_000_000, interest_expense=5_000_000)


def test_net_debt():
    assert net_debt(35_000_000, 4_000_000) == 31_000_000


def test_leverage_matches_build_plan_example():
    assert math.isclose(leverage(35_000_000, 8_000_000), 4.375)


def test_net_leverage():
    assert math.isclose(net_leverage(35_000_000, 4_000_000, 8_000_000), 31_000_000 / 8_000_000)


def test_interest_cover_matches_build_plan_example():
    assert math.isclose(interest_cover(8_000_000, 5_000_000), 1.6)


def test_ebitda_margin():
    assert math.isclose(ebitda_margin(8_000_000, 50_000_000), 0.16)


def test_compute_ratios_bundle():
    r = compute_ratios(**ABC)
    assert r.net_debt == 31_000_000
    assert math.isclose(r.leverage, 4.375)
    assert math.isclose(r.interest_cover, 1.6)
    assert math.isclose(r.ebitda_margin, 0.16)


def test_division_by_zero_returns_none_not_exception():
    assert leverage(35_000_000, 0) is None
    assert interest_cover(8_000_000, 0) is None
    assert ebitda_margin(8_000_000, 0) is None


def test_missing_inputs_return_none():
    assert leverage(None, 8_000_000) is None
    assert net_debt(None, 4_000_000) is None


def test_pct_change_basic():
    assert math.isclose(pct_change(90, 100), -0.10)
    assert math.isclose(pct_change(110, 100), 0.10)


def test_pct_change_guards_zero_and_missing():
    assert pct_change(100, 0) is None
    assert pct_change(None, 100) is None
    assert pct_change(100, None) is None


def test_period_changes_first_period_has_no_deltas():
    changes = compute_period_changes(ABC, None)
    assert changes.ebitda_change is None
    assert changes.revenue_change is None
    assert changes.cash_change is None
    assert changes.leverage_change is None
    # But the current-period ratio itself is still computable.
    assert math.isclose(changes.interest_cover_current, 1.6)


def test_period_changes_second_period():
    previous = dict(revenue=55_000_000, ebitda=10_000_000, debt=30_000_000, cash=6_000_000, interest_expense=4_500_000)
    changes = compute_period_changes(ABC, previous)
    assert math.isclose(changes.ebitda_change, (8_000_000 - 10_000_000) / 10_000_000)
    assert math.isclose(changes.revenue_change, (50_000_000 - 55_000_000) / 55_000_000)
    assert math.isclose(changes.cash_change, (4_000_000 - 6_000_000) / 6_000_000)
    prev_leverage = 30_000_000 / 10_000_000
    curr_leverage = 35_000_000 / 8_000_000
    assert math.isclose(changes.leverage_change, curr_leverage - prev_leverage)

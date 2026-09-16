"""
PD overlay tests, anchored on the Week 6 worked example from the build plan:

    Input PD 6.00% | Risk multiplier 2.00 | Calculated PD 11.64%
"""

import math

import pytest

from credit.early_warning import RiskBand
from credit.pd_overlay import (
    band_multiplier,
    hazard_rate,
    implied_multiplier,
    stressed_pd,
    stressed_pd_from_band,
)


def test_build_plan_worked_example():
    pd_star = stressed_pd(0.06, 2.00)
    assert round(pd_star * 100, 2) == 11.64


def test_multiplier_one_is_a_no_op():
    assert math.isclose(stressed_pd(0.08, 1.0), 0.08, rel_tol=1e-9)


def test_multiplier_zero_gives_zero_pd():
    assert stressed_pd(0.08, 0.0) == 0.0


def test_pd_increases_monotonically_with_multiplier():
    pd0 = 0.05
    prev = stressed_pd(pd0, 1.0)
    for m in (1.5, 2.0, 2.5, 3.0, 4.0):
        cur = stressed_pd(pd0, m)
        assert cur > prev
        prev = cur


def test_pd_never_reaches_or_exceeds_one():
    pd_star = stressed_pd(0.20, 20.0)
    assert 0.0 <= pd_star < 1.0


def test_band_multipliers_match_build_plan():
    assert band_multiplier(RiskBand.GREEN) == 1.0
    assert band_multiplier(RiskBand.AMBER) == 1.5
    assert band_multiplier(RiskBand.RED) == 2.5
    assert band_multiplier(RiskBand.CRITICAL) == 4.0


def test_stressed_pd_from_band_uses_the_right_multiplier():
    pd0 = 0.04
    assert math.isclose(stressed_pd_from_band(pd0, RiskBand.GREEN), pd0)
    assert stressed_pd_from_band(pd0, RiskBand.CRITICAL) > stressed_pd_from_band(pd0, RiskBand.RED)
    assert stressed_pd_from_band(pd0, RiskBand.RED) > stressed_pd_from_band(pd0, RiskBand.AMBER)
    assert stressed_pd_from_band(pd0, RiskBand.AMBER) > stressed_pd_from_band(pd0, RiskBand.GREEN)


def test_invalid_pd0_raises():
    with pytest.raises(ValueError):
        stressed_pd(1.0, 2.0)
    with pytest.raises(ValueError):
        stressed_pd(-0.1, 2.0)


def test_negative_multiplier_raises():
    with pytest.raises(ValueError):
        stressed_pd(0.05, -1.0)


def test_implied_multiplier_round_trips():
    pd0, m = 0.05, 2.3
    pd_star = stressed_pd(pd0, m)
    assert math.isclose(implied_multiplier(pd0, pd_star), m, rel_tol=1e-6)

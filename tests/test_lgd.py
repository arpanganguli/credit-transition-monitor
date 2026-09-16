"""LGD overlay tests: band uplift, collateral coverage, and clamping."""

import math

from credit.early_warning import RiskBand
from credit.lgd_overlay import (
    LGD_CEILING,
    LGD_FLOOR,
    collateral_coverage_ratio,
    lgd_band_multiplier,
    stressed_lgd,
)


def test_coverage_ratio_basic():
    assert math.isclose(collateral_coverage_ratio(5_000_000, 10_000_000), 0.5)


def test_coverage_ratio_capped_at_one():
    assert collateral_coverage_ratio(20_000_000, 10_000_000) == 1.0


def test_coverage_ratio_handles_missing_or_zero_ead():
    assert collateral_coverage_ratio(1_000_000, 0) == 0.0
    assert collateral_coverage_ratio(None, 10_000_000) == 0.0
    assert collateral_coverage_ratio(1_000_000, None) == 0.0


def test_band_multipliers_are_non_decreasing_with_severity():
    order = [RiskBand.GREEN, RiskBand.AMBER, RiskBand.RED, RiskBand.CRITICAL]
    mults = [lgd_band_multiplier(b) for b in order]
    assert mults == sorted(mults)
    assert mults[0] == 1.0


def test_stressed_lgd_worse_band_gives_higher_lgd_for_same_collateral():
    kwargs = dict(baseline_lgd=0.40, collateral_value=5_000_000, ead_baseline=10_000_000)
    green = stressed_lgd(band=RiskBand.GREEN, **kwargs)
    critical = stressed_lgd(band=RiskBand.CRITICAL, **kwargs)
    assert critical > green


def test_more_collateral_reduces_lgd():
    low_cover = stressed_lgd(0.40, RiskBand.RED, collateral_value=0, ead_baseline=10_000_000)
    high_cover = stressed_lgd(0.40, RiskBand.RED, collateral_value=10_000_000, ead_baseline=10_000_000)
    assert high_cover < low_cover


def test_lgd_is_clamped_to_bounds():
    # An extreme collateral credit should never push LGD below the floor.
    assert stressed_lgd(0.01, RiskBand.GREEN, collateral_value=100_000_000, ead_baseline=1_000) >= LGD_FLOOR
    # A very high baseline LGD under CRITICAL uplift should never exceed the ceiling.
    assert stressed_lgd(0.95, RiskBand.CRITICAL, collateral_value=0, ead_baseline=10_000_000) <= LGD_CEILING


def test_no_collateral_data_still_returns_a_valid_lgd():
    lgd = stressed_lgd(0.40, RiskBand.AMBER, collateral_value=None, ead_baseline=None)
    assert LGD_FLOOR <= lgd <= LGD_CEILING

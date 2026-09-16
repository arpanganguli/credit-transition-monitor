"""
Early-warning scorecard tests, anchored on the Week 6 worked example:

    Risk score: Leverage +20 | EBITDA +15 | Interest cover +15 | Liquidity +10
    Total: 60  ->  risk band = RED
"""

from credit.early_warning import RiskBand, compute_scorecard, score_to_band


def test_build_plan_worked_example_total_and_band():
    sc = compute_scorecard(
        ebitda_change=-0.24,
        leverage_change=None,
        leverage_current=5.3,
        max_leverage=5.0,
        interest_cover_current=1.4,
        covenant_headroom=None,
        covenant_breached=False,
        cash_change=-0.31,
        revenue_change=None,
    )
    assert sc.score == 60
    assert sc.band == RiskBand.RED
    points = {r.family: r.points for r in sc.reasons}
    assert points["leverage"] == 20
    assert points["ebitda"] == 15
    assert points["interest_cover"] == 15
    assert points["cash"] == 10


def test_band_boundaries():
    assert score_to_band(0) == RiskBand.GREEN
    assert score_to_band(24) == RiskBand.GREEN
    assert score_to_band(25) == RiskBand.AMBER
    assert score_to_band(49) == RiskBand.AMBER
    assert score_to_band(50) == RiskBand.RED
    assert score_to_band(74) == RiskBand.RED
    assert score_to_band(75) == RiskBand.CRITICAL
    assert score_to_band(100) == RiskBand.CRITICAL


def test_no_signals_gives_zero_green():
    sc = compute_scorecard(
        ebitda_change=0.05, leverage_change=-0.2, leverage_current=2.0, max_leverage=4.0,
        interest_cover_current=4.0, covenant_headroom=0.5, covenant_breached=False,
        cash_change=0.02, revenue_change=0.03,
    )
    assert sc.score == 0
    assert sc.band == RiskBand.GREEN
    assert sc.reasons == []


def test_family_takes_max_not_sum_of_tiers():
    """Interest cover <1.0x should score +20, not +35 (15 + 20) -- tiers, not add-ons."""
    sc = compute_scorecard(
        ebitda_change=None, leverage_change=None, leverage_current=None, max_leverage=None,
        interest_cover_current=0.8, covenant_headroom=None, covenant_breached=False,
        cash_change=None, revenue_change=None,
    )
    assert sc.score == 20


def test_covenant_breach_dominates_headroom_warning():
    sc = compute_scorecard(
        ebitda_change=None, leverage_change=None, leverage_current=None, max_leverage=None,
        interest_cover_current=None, covenant_headroom=0.05, covenant_breached=True,
        cash_change=None, revenue_change=None,
    )
    assert sc.score == 25


def test_score_is_capped_at_100():
    sc = compute_scorecard(
        ebitda_change=-0.5, leverage_change=2.0, leverage_current=10.0, max_leverage=3.0,
        interest_cover_current=0.2, covenant_headroom=0.0, covenant_breached=True,
        cash_change=-0.6, revenue_change=-0.4,
    )
    assert sc.score <= 100


def test_improving_metrics_never_score_points():
    sc = compute_scorecard(
        ebitda_change=0.3, leverage_change=-0.5, leverage_current=1.5, max_leverage=4.0,
        interest_cover_current=5.0, covenant_headroom=0.8, covenant_breached=False,
        cash_change=0.4, revenue_change=0.2,
    )
    assert sc.score == 0

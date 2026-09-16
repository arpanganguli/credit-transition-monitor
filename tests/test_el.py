"""
Expected loss and attribution tests. Anchored on the Week 1 worked example
(EL = 486,000 for EAD=18m, PD=6%, LGD=45%) and the Shapley-attribution
"efficiency" property required by Week 5: contributions must sum exactly to
Delta EL, for any two states.
"""

import math
import random

from credit.attribution import attribute_delta_el, shapley_decomposition
from credit.expected_loss import delta_expected_loss, delta_expected_loss_pct, expected_loss


def test_expected_loss_worked_example():
    assert expected_loss(18_000_000, 0.06, 0.45) == 486_000


def test_delta_expected_loss():
    assert delta_expected_loss(1_110_780, 486_000) == 624_780


def test_delta_expected_loss_none_when_no_previous():
    assert delta_expected_loss(500_000, None) is None


def test_delta_expected_loss_pct():
    assert math.isclose(delta_expected_loss_pct(110, 100), 0.10)
    assert delta_expected_loss_pct(110, None) is None
    assert delta_expected_loss_pct(110, 0) is None


def test_shapley_efficiency_property_random_cases():
    """Contributions must always sum exactly to the total change, for any inputs."""
    rng = random.Random(7)
    for _ in range(200):
        before = {"ead": rng.uniform(1e6, 5e7), "pd": rng.uniform(0.001, 0.3), "lgd": rng.uniform(0.05, 0.9)}
        after = {"ead": rng.uniform(1e6, 5e7), "pd": rng.uniform(0.001, 0.3), "lgd": rng.uniform(0.05, 0.9)}
        contributions = shapley_decomposition(before, after, value_fn=lambda ead, pd, lgd: ead * pd * lgd)
        total_change = (after["ead"] * after["pd"] * after["lgd"]) - (before["ead"] * before["pd"] * before["lgd"])
        assert math.isclose(sum(contributions.values()), total_change, rel_tol=1e-9, abs_tol=1e-6)


def test_attribute_delta_el_matches_build_plan_worked_example():
    result = attribute_delta_el(
        ead_baseline=18_000_000, pd_baseline=0.06, lgd_baseline=0.45,
        ead_current=18_000_000, pd_current=0.121, lgd_current=0.51,
    )
    assert result.el_baseline == 486_000
    assert math.isclose(result.el_current, 18_000_000 * 0.121 * 0.51)
    assert math.isclose(sum(result.contributions.values()), result.delta_el, rel_tol=1e-9)
    # EAD did not move in this scenario, so it must contribute exactly zero.
    assert math.isclose(result.contributions["ead"], 0.0, abs_tol=1e-6)
    # PD moved from 6% to 12.1% (roughly doubling) and should dominate the
    # attribution over the milder LGD move (45% -> 51%).
    assert result.contributions["pd"] > result.contributions["lgd"] > 0


def test_zero_delta_gives_zero_contributions():
    result = attribute_delta_el(
        ead_baseline=10_000_000, pd_baseline=0.05, lgd_baseline=0.40,
        ead_current=10_000_000, pd_current=0.05, lgd_current=0.40,
    )
    assert result.delta_el == 0.0
    assert all(math.isclose(v, 0.0, abs_tol=1e-9) for v in result.contributions.values())
    assert result.shares() == {"ead": 0.0, "pd": 0.0, "lgd": 0.0}

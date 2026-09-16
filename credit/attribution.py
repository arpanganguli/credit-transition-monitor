"""
Expected-loss attribution: explain a Delta EL, don't just report it.

EL = EAD x PD x LGD is a product of three factors, so moving from a baseline
(EAD0, PD0, LGD0) to a current (EAD1, PD1, LGD1) state can be decomposed into
"how much of the change came from EAD, how much from PD, how much from LGD".

Because EL is multiplicative, the answer depends on the order you imagine
changing the factors in (change PD first or EAD first gives different
intermediate values). Shapley attribution removes that arbitrariness: it
averages the marginal contribution of each factor across every possible
order, which is exactly the build plan's instruction ("average marginal
effects across possible calculation orders").

This has the "efficiency" property that matters for a credit committee: the
three contributions always sum exactly to the total Delta EL, so nothing is
left unexplained and nothing double-counts.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Callable

FACTOR_NAMES = ("ead", "pd", "lgd")


def _el(ead: float, pd: float, lgd: float) -> float:
    return ead * pd * lgd


@dataclass
class AttributionResult:
    """EL attribution for a single borrower between two periods."""

    el_baseline: float
    el_current: float
    delta_el: float
    contributions: dict[str, float]  # {"ead": ..., "pd": ..., "lgd": ...}

    def shares(self) -> dict[str, float]:
        """Each contribution as a fraction of |Delta EL| (None-safe: 0 if Delta EL is 0)."""
        denom = abs(self.delta_el)
        if denom == 0:
            return {k: 0.0 for k in self.contributions}
        return {k: v / self.delta_el if self.delta_el != 0 else 0.0 for k, v in self.contributions.items()}

    def to_dict(self) -> dict:
        return {
            "el_baseline": self.el_baseline,
            "el_current": self.el_current,
            "delta_el": self.delta_el,
            "contributions": dict(self.contributions),
            "shares": self.shares(),
        }


def shapley_decomposition(
    before: dict[str, float],
    after: dict[str, float],
    value_fn: Callable[..., float] = _el,
) -> dict[str, float]:
    """
    Generic Shapley-style decomposition of value_fn(**after) - value_fn(**before)
    across the keys shared by ``before`` and ``after``.

    For each of the N! orderings of the factor names, walk the factors from
    ``before`` to ``after`` in that order and record each factor's marginal
    contribution at the point it flips; average across all orderings.

    This is O(N! x N) -- fine for the 3 factors (EAD, PD, LGD) this module is
    built for; do not reuse this for a large factor count without switching
    to a sampling-based Shapley estimator.
    """
    names = list(before.keys())
    contributions = {n: 0.0 for n in names}
    perms = list(permutations(names))

    for perm in perms:
        state = dict(before)
        for name in perm:
            value_before = value_fn(**state)
            state[name] = after[name]
            value_after = value_fn(**state)
            contributions[name] += value_after - value_before

    n_perms = len(perms)
    return {name: total / n_perms for name, total in contributions.items()}


def attribute_delta_el(
    ead_baseline: float,
    pd_baseline: float,
    lgd_baseline: float,
    ead_current: float,
    pd_current: float,
    lgd_current: float,
) -> AttributionResult:
    """Decompose a borrower's Delta EL into EAD / PD / LGD contributions."""
    before = {"ead": ead_baseline, "pd": pd_baseline, "lgd": lgd_baseline}
    after = {"ead": ead_current, "pd": pd_current, "lgd": lgd_current}

    el_baseline = _el(**before)
    el_current = _el(**after)
    contributions = shapley_decomposition(before, after)

    return AttributionResult(
        el_baseline=el_baseline,
        el_current=el_current,
        delta_el=el_current - el_baseline,
        contributions=contributions,
    )

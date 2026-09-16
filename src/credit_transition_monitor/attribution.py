from itertools import permutations
import numpy as np

FACTORS = ("ead", "pd", "lgd")
def shapley_el(before, after):
    """Exact average of all six orders; signed currency contributions."""
    b = np.asarray(before, dtype=float)
    a = np.asarray(after, dtype=float)
    if b.shape != (3,) or a.shape != (3,) or not np.isfinite([b,a]).all():
        raise ValueError("Pass finite [EAD, PD, LGD] triples")
    contribution = np.zeros(3)
    for order in permutations(range(3)):
        state = b.copy()
        for i in order:
            old = state.prod()
            state[i] = a[i]
            contribution[i] += (state.prod() - old) / 6
    return dict(zip(FACTORS, contribution))

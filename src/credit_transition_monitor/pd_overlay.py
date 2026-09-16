import numpy as np

def calculate_stressed_pd(baseline_pd, multiplier):
    p, m = np.asarray(baseline_pd, dtype=float), np.asarray(multiplier, dtype=float)
    if np.any(~np.isfinite(p)) or np.any((p < 0) | (p > 1)) or np.any(~np.isfinite(m)) or np.any(m < 1):
        raise ValueError("PD must be in [0,1]; multiplier must be finite and >=1")
    with np.errstate(divide="ignore"):
        return -np.expm1(m * np.log1p(-p))

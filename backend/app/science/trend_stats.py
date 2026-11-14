"""Mann-Kendall trend test and Sen's slope estimator for annual series.

Standard non-parametric trend tools (Mann 1945; Kendall 1975; Sen 1968).
No external stats dependency beyond numpy/scipy's normal CDF.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm


def mann_kendall_test(values: list[float]) -> dict:
    """Returns {"trend": "increasing"|"decreasing"|"no trend", "p_value": float,
    "z": float, "s": int} for a 1-D series ordered by time. NaNs are dropped
    pairwise is not performed -- caller should pass only non-null years."""
    x = np.asarray(values, dtype=float)
    n = len(x)
    if n < 4:
        return {"trend": "no trend", "p_value": None, "z": None, "s": None}

    s = 0
    for k in range(n - 1):
        s += np.sum(np.sign(x[k + 1 :] - x[k]))

    # variance, adjusted for ties
    unique, counts = np.unique(x, return_counts=True)
    tie_term = np.sum(counts * (counts - 1) * (2 * counts + 5))
    var_s = (n * (n - 1) * (2 * n + 5) - tie_term) / 18.0

    if s > 0:
        z = (s - 1) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / math.sqrt(var_s)
    else:
        z = 0.0

    p_value = 2 * (1 - norm.cdf(abs(z)))

    if p_value < 0.10 and z > 0:
        trend = "increasing"
    elif p_value < 0.10 and z < 0:
        trend = "decreasing"
    else:
        trend = "no trend"

    return {"trend": trend, "p_value": round(float(p_value), 4), "z": round(float(z), 4), "s": int(s)}


def sens_slope(values: list[float], time_index: list[float] | None = None) -> float | None:
    """Sen's slope estimator: median of all pairwise slopes (x_j - x_i) / (j - i).

    time_index defaults to 0..n-1 (i.e. one unit per observation, e.g. years
    if values are one-per-year).
    """
    x = np.asarray(values, dtype=float)
    n = len(x)
    if n < 2:
        return None
    t = np.asarray(time_index, dtype=float) if time_index is not None else np.arange(n, dtype=float)

    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            dt = t[j] - t[i]
            if dt != 0:
                slopes.append((x[j] - x[i]) / dt)

    if not slopes:
        return None
    return round(float(np.median(slopes)), 5)

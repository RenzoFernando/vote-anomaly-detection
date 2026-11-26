"""Summarize participation in prepared simulated election records."""

import numpy as np
import pandas as pd

from src._participation import participation_rates


def summarize_data(prepared: pd.DataFrame) -> dict:
    """Return record counts and descriptive statistics as strict JSON values.

    Missing source values, nonnumeric values and infinities are counted
    separately. Only finite rates contribute to the statistics, including
    rates outside [0, 1]. Quartiles use linear interpolation. The standard
    deviation is sample-based (ddof=1). Undefined statistics, including the
    above-100% count when no rate is finite, are None.
    """
    rates = participation_rates(prepared)
    missing = prepared["participation_rate"].isna()
    finite = rates[np.isfinite(rates)]
    q1, q3 = finite.quantile([0.25, 0.75], interpolation="linear")
    statistics = {
        "mean": finite.mean(),
        "median": finite.median(),
        "min": finite.min(),
        "max": finite.max(),
        "q1": q1,
        "q3": q3,
        "std": finite.std(ddof=1),
    }

    return {
        "record_count": len(prepared),
        "finite_participation_count": len(finite),
        "missing_participation_count": int(missing.sum()),
        "nonfinite_participation_count": int(np.isinf(rates).sum()),
        "invalid_participation_count": int((rates.isna() & ~missing).sum()),
        "over_100_percent_count": int(finite.gt(1).sum()) if len(finite) else None,
        "participation_rate": {
            name: float(value) if np.isfinite(value) else None
            for name, value in statistics.items()
        },
    }

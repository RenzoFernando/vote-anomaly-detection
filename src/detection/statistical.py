"""Detect unusual participation rates using Tukey's 1.5 IQR fences."""

import numpy as np
import pandas as pd

from src._participation import participation_rates


ALERT_COLUMNS = ("record_id", "method", "reason")


def detect_statistical_anomalies(prepared: pd.DataFrame) -> pd.DataFrame:
    """Return one statistical alert per outlying record, in input order.

    Use at least four finite rates, including values outside [0, 1]. Use
    pandas' linear quartiles and strict comparisons, including when IQR is zero
    and both fences coincide. Exclude missing, invalid and infinite rates.
    Missing, blank or repeated record IDs after trimming raise ValueError.
    Repeated station IDs do not affect this calculation.
    """
    rates = participation_rates(prepared)
    if "record_id" not in prepared or not isinstance(prepared["record_id"], pd.Series):
        raise ValueError("Prepared election records require a single record_id column.")
    record_ids = prepared["record_id"].astype("string").str.strip()
    if record_ids.isna().any() or record_ids.eq("").any():
        raise ValueError("record_id values must not be missing or blank.")
    if record_ids.duplicated().any():
        raise ValueError("record_id values must be unique.")

    finite_mask = np.isfinite(rates)
    finite = rates[finite_mask]
    if len(finite) < 4:
        return pd.DataFrame(columns=ALERT_COLUMNS)

    q1, q3 = finite.quantile([0.25, 0.75], interpolation="linear")
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    alerts = []
    for record_id, rate in zip(record_ids[finite_mask], finite):
        if rate < lower:
            reason = f"participation_rate {rate} is below IQR lower bound {lower}."
        elif rate > upper:
            reason = f"participation_rate {rate} is above IQR upper bound {upper}."
        else:
            continue
        alerts.append((record_id, "statistical", reason))

    return pd.DataFrame(alerts, columns=ALERT_COLUMNS)

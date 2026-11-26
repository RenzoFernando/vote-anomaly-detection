"""Interpret prepared participation rates consistently across Luna's analyses."""

import numpy as np
import pandas as pd


def _parse_rate(value: object) -> float:
    if isinstance(value, (bool, np.bool_, complex, np.complexfloating)):
        return np.nan
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return np.nan


def participation_rates(prepared: pd.DataFrame) -> pd.Series:
    """Read real numbers and numeric strings, preserving infinities for classification."""
    if not isinstance(prepared, pd.DataFrame):
        raise TypeError("Prepared election records must be a pandas DataFrame.")
    if "participation_rate" not in prepared:
        raise ValueError("Prepared election records require a participation_rate column.")
    rates = prepared["participation_rate"]
    if not isinstance(rates, pd.Series):
        raise ValueError("Prepared election records require a single participation_rate column.")
    return rates.map(_parse_rate).astype(float)

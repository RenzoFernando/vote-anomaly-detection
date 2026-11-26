"""Detect logical inconsistencies in simulated election records with explicit rules.

Each rule is a small, independent function that returns a boolean mask over the
prepared records. ``detect_rule_anomalies`` applies every rule and emits one alert
per (record, rule) so the report can explain *why* a record was flagged.

Rules never use the ground-truth labels and never drop or modify records.
"""

from collections.abc import Callable

import pandas as pd

from src.preprocessing import BALLOT_COLUMNS, COUNT_COLUMNS, REQUIRED_COLUMNS


ALERT_COLUMNS = ("record_id", "method", "reason")
METHOD = "rule"


def _numeric(prepared: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    """Read count columns as floats; unreadable values become NaN (never raise)."""
    return prepared.loc[:, list(columns)].apply(pd.to_numeric, errors="coerce")


def rule_missing_values(prepared: pd.DataFrame) -> pd.Series:
    """R1: any required field is missing or an identifier is blank."""
    counts = _numeric(prepared, COUNT_COLUMNS)
    ids = prepared[["record_id", "station_id"]].astype("string")
    blank_ids = ids.isna().any(axis=1) | ids.apply(lambda col: col.str.strip().eq("")).any(axis=1)
    return counts.isna().any(axis=1) | blank_ids.fillna(True)


def rule_negative_counts(prepared: pd.DataFrame) -> pd.Series:
    """R2: no count (census, ballot category or total) can be negative."""
    return _numeric(prepared, COUNT_COLUMNS).lt(0).any(axis=1)


def rule_vote_total_mismatch(prepared: pd.DataFrame) -> pd.Series:
    """R3: total_votes must equal the sum of all five ballot categories."""
    counts = _numeric(prepared, (*BALLOT_COLUMNS, "total_votes"))
    ballot_sum = counts[list(BALLOT_COLUMNS)].sum(axis=1, min_count=len(BALLOT_COLUMNS))
    return ballot_sum.notna() & counts["total_votes"].notna() & ballot_sum.ne(counts["total_votes"])


def rule_turnout_over_capacity(prepared: pd.DataFrame) -> pd.Series:
    """R4: a station cannot count more votes than it has registered voters."""
    counts = _numeric(prepared, ("registered_voters", "total_votes"))
    return counts["total_votes"].gt(counts["registered_voters"]).fillna(False)


def rule_duplicate_station_id(prepared: pd.DataFrame) -> pd.Series:
    """R5: a station_id may appear only once.

    The first occurrence is kept as the reference and later repeats are flagged,
    because the data alone cannot say which of the copies is the legitimate one.
    Flagging every copy would double the false positives for each duplicated pair.
    """
    stations = prepared["station_id"].astype("string").str.strip()
    usable = stations.notna() & stations.ne("")
    return stations.duplicated(keep="first") & usable


RULES: tuple[tuple[str, str, Callable[[pd.DataFrame], pd.Series]], ...] = (
    ("R1", "missing or blank value", rule_missing_values),
    ("R2", "negative count", rule_negative_counts),
    ("R3", "total_votes differs from the sum of ballot categories", rule_vote_total_mismatch),
    ("R4", "total_votes exceeds registered_voters", rule_turnout_over_capacity),
    ("R5", "station_id repeated", rule_duplicate_station_id),
)


def detect_rule_anomalies(prepared: pd.DataFrame) -> pd.DataFrame:
    """Return one alert per (record, violated rule), grouped by rule in input order.

    Raises ValueError if required columns are missing or record_id is not a usable key
    (missing, blank or repeated after trimming), since alerts are keyed by record_id.
    """
    if not isinstance(prepared, pd.DataFrame):
        raise TypeError("Prepared election records must be a pandas DataFrame.")
    missing = sorted(set(REQUIRED_COLUMNS) - set(prepared.columns))
    if missing:
        raise ValueError(f"Prepared records are missing required columns: {missing}")

    record_ids = prepared["record_id"].astype("string").str.strip()
    if record_ids.isna().any() or record_ids.eq("").any():
        raise ValueError("record_id values must not be missing or blank.")
    if record_ids.duplicated().any():
        raise ValueError("record_id values must be unique.")

    alerts = []
    for code, description, rule in RULES:
        mask = rule(prepared).fillna(False).astype(bool)
        alerts.extend(
            (record_id, METHOD, f"{code}: {description}.") for record_id in record_ids[mask.to_numpy()]
        )
    return pd.DataFrame(alerts, columns=ALERT_COLUMNS)

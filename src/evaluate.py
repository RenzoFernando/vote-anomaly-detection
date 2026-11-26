"""Evaluate simulated anomaly detection at the record level."""

from collections.abc import Iterable

import pandas as pd


DETECTION_METHODS = ("rule", "statistical")


def _record_ids(values: Iterable[str], source: str) -> pd.Series:
    ids = pd.Series(values, dtype="string").str.strip()
    if ids.isna().any() or ids.eq("").any():
        raise ValueError(f"{source} contains missing or blank record_id values.")
    return ids


def _evaluation_inputs(
    alerts: pd.DataFrame,
    ground_truth: pd.DataFrame,
    record_ids: Iterable[str],
) -> tuple[set[str], pd.Series, pd.Series]:
    population = _record_ids(record_ids, "Dataset")
    if population.duplicated().any():
        raise ValueError("Dataset record_id values must be unique.")
    universe = set(population)

    for frame, source in ((alerts, "Alerts"), (ground_truth, "Ground truth")):
        if "record_id" not in frame:
            raise ValueError(f"{source} is missing the record_id column.")

    predicted = _record_ids(alerts["record_id"], "Alerts")
    labels = _record_ids(ground_truth["record_id"], "Ground truth")
    if labels.duplicated().any():
        raise ValueError("Ground truth record_id values must be unique.")
    for ids, source in ((predicted, "Alerts"), (labels, "Ground truth")):
        if unknown := set(ids) - universe:
            examples = ", ".join(sorted(unknown)[:5])
            raise ValueError(
                f"{source} contains record_id values outside the dataset: {examples}"
            )

    return universe, predicted, labels


def _score(
    predicted: set[str], actual: set[str], universe: set[str]
) -> dict[str, int | float | list[list[int]]]:
    tp = len(predicted & actual)
    fp = len(predicted - actual)
    fn = len(actual - predicted)
    tn = len(universe - (predicted | actual))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0

    return {
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": [[tn, fp], [fn, tp]],
    }


def evaluate_detection(
    alerts: pd.DataFrame,
    ground_truth: pd.DataFrame,
    record_ids: Iterable[str],
) -> dict[str, int | float | list[list[int]]]:
    """Compare unique alerted IDs with the positive-only labels in the dataset.

    Both frames require record_id. The dataset IDs define the evaluation
    population, including the negatives absent from the ground truth CSV.
    """
    universe, alerted_ids, labeled_ids = _evaluation_inputs(alerts, ground_truth, record_ids)
    return _score(set(alerted_ids), set(labeled_ids), universe)


def evaluate_breakdown(
    alerts: pd.DataFrame,
    ground_truth: pd.DataFrame,
    record_ids: Iterable[str],
    available_methods: Iterable[str],
) -> tuple[dict, dict]:
    """Return combined metrics and details for the detectors that ran."""
    universe, alerted_ids, labeled_ids = _evaluation_inputs(alerts, ground_truth, record_ids)
    available = set(available_methods)
    if not available.issubset(DETECTION_METHODS):
        raise ValueError("Unknown evaluation method.")
    if not alerts["method"].isin(available).all():
        raise ValueError("Alerts contain a method that did not run.")

    predicted = set(alerted_ids)
    actual = set(labeled_ids)
    predictions = {
        method: set(alerted_ids[alerts["method"].eq(method)])
        for method in DETECTION_METHODS
        if method in available
    }
    by_method = {
        method: _score(predictions[method], actual, universe) if method in available else None
        for method in DETECTION_METHODS
    }

    types = ground_truth.get("anomaly_type", pd.Series(index=ground_truth.index, dtype="string"))
    types = types.astype("string").str.strip().replace("", pd.NA)
    types_by_id = dict(zip(labeled_ids, (str(kind) if pd.notna(kind) else None for kind in types)))
    ids_by_type: dict[str | None, set[str]] = {}
    for record_id, kind in types_by_id.items():
        ids_by_type.setdefault(kind, set()).add(record_id)

    incremental = None
    shared = None
    if len(predictions) == len(DETECTION_METHODS):
        rule = predictions["rule"]
        statistical = predictions["statistical"]
        shared = rule & statistical
        additional = statistical - rule
        incremental = {
            "additional_tp": len(additional & actual),
            "additional_fp": len(additional - actual),
        }

    by_type = [
        {
            "anomaly_type": kind,
            "injected": len(ids),
            **{method: len(ids & predictions[method]) if method in available else None
               for method in DETECTION_METHODS},
            "both": len(ids & shared) if shared is not None else None,
            "combined": len(ids & predicted),
        }
        for kind, ids in sorted(ids_by_type.items(), key=lambda item: item[0] or "")
    ]

    false_positive_ids = predicted - actual
    findings: dict[str, set[tuple[str, str]]] = {}
    for record_id, method, reason in zip(alerted_ids, alerts["method"], alerts["reason"]):
        if record_id in false_positive_ids and pd.notna(reason):
            findings.setdefault(record_id, set()).add((method, str(reason)))

    details = {
        "by_method": by_method,
        "by_anomaly_type": by_type,
        "statistical_increment": incremental,
        "false_positives": [
            {
                "record_id": record_id,
                "findings": [
                    {"method": method, "reason": reason}
                    for method, reason in sorted(findings.get(record_id, ()))
                ],
            }
            for record_id in sorted(false_positive_ids)
        ],
        "false_negatives": [
            {"record_id": record_id, "anomaly_type": types_by_id[record_id]}
            for record_id in sorted(actual - predicted)
        ],
    }
    return _score(predicted, actual, universe), details

"""Evaluate simulated anomaly detection at the record level."""

from collections.abc import Iterable

import pandas as pd


def _record_ids(values: Iterable[str], source: str) -> pd.Series:
    ids = pd.Series(values, dtype="string").str.strip()
    if ids.isna().any() or ids.eq("").any():
        raise ValueError(f"{source} contains missing or blank record_id values.")
    return ids


def evaluate_detection(
    alerts: pd.DataFrame,
    ground_truth: pd.DataFrame,
    record_ids: Iterable[str],
) -> dict[str, int | float | list[list[int]]]:
    """Compare unique alerted IDs with the positive-only labels in the dataset.

    Both frames require record_id. The dataset IDs define the evaluation
    population, including the negatives absent from the ground truth CSV.
    """
    population = _record_ids(record_ids, "Dataset")
    if population.duplicated().any():
        raise ValueError("Dataset record_id values must be unique.")
    universe = set(population)

    for frame, source in ((alerts, "Alerts"), (ground_truth, "Ground truth")):
        if "record_id" not in frame:
            raise ValueError(f"{source} is missing the record_id column.")

    predicted = set(_record_ids(alerts["record_id"], "Alerts"))
    labels = _record_ids(ground_truth["record_id"], "Ground truth")
    if labels.duplicated().any():
        raise ValueError("Ground truth record_id values must be unique.")
    actual = set(labels)

    for ids, source in ((predicted, "Alerts"), (actual, "Ground truth")):
        if unknown := ids - universe:
            examples = ", ".join(sorted(unknown)[:5])
            raise ValueError(
                f"{source} contains record_id values outside the dataset: {examples}"
            )

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

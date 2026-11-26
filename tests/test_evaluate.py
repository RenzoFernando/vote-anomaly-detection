import pandas as pd
import pytest

from src.evaluate import evaluate_detection


def test_evaluates_unique_alerted_records_against_sparse_labels():
    alerts = pd.DataFrame(
        {"record_id": ["A", "A", "B"], "method": ["rule", "statistical", "rule"]}
    )
    labels = pd.DataFrame({"record_id": ["A", "C"]})

    assert evaluate_detection(alerts, labels, ["A", "B", "C", "D"]) == {
        "TP": 1,
        "FP": 1,
        "FN": 1,
        "TN": 1,
        "precision": 0.5,
        "recall": 0.5,
        "f1": 0.5,
        "confusion_matrix": [[1, 1], [1, 1]],
    }


@pytest.mark.parametrize(
    ("predicted", "actual", "matrix"),
    [
        ([], [], [[3, 0], [0, 0]]),
        ([], ["A", "B"], [[1, 0], [2, 0]]),
        (["A"], [], [[2, 1], [0, 0]]),
    ],
)
def test_handles_zero_denominators(predicted, actual, matrix):
    metrics = evaluate_detection(
        pd.DataFrame({"record_id": predicted}),
        pd.DataFrame({"record_id": actual}),
        ["A", "B", "C"],
    )

    assert metrics["confusion_matrix"] == matrix
    assert metrics["precision"] == metrics["recall"] == metrics["f1"] == 0.0


@pytest.mark.parametrize(
    ("predicted", "actual", "population", "message"),
    [
        (["B"], [], ["A"], "Alerts contains.*outside"),
        ([], ["B"], ["A"], "Ground truth contains.*outside"),
        ([], [], ["A", " A "], "Dataset record_id values must be unique"),
        ([], ["A", "A"], ["A"], "Ground truth record_id values must be unique"),
        ([], [], [None], "Dataset contains missing or blank"),
        ([" "], [], ["A"], "Alerts contains missing or blank"),
    ],
)
def test_rejects_invalid_ids(predicted, actual, population, message):
    with pytest.raises(ValueError, match=message):
        evaluate_detection(
            pd.DataFrame({"record_id": predicted}),
            pd.DataFrame({"record_id": actual}),
            population,
        )

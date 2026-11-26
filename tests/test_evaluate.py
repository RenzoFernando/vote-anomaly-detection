import pandas as pd
import pytest

from src.evaluate import evaluate_breakdown, evaluate_detection


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


def test_breakdown_counts_overlap_and_exclusive_statistical_findings():
    alerts = pd.DataFrame(
        [
            ("A", "rule", "rule finding"),
            ("A", "statistical", "same record"),
            ("B", "statistical", "exclusive detection"),
            ("D", "statistical", "exclusive false alarm"),
            ("D", "statistical", "exclusive false alarm"),
        ],
        columns=["record_id", "method", "reason"],
    )
    labels = pd.DataFrame({"record_id": ["A", "B", "C"], "anomaly_type": ["x", "x", "y"]})

    metrics, details = evaluate_breakdown(alerts, labels, list("ABCDE"), ("rule", "statistical"))

    assert metrics == evaluate_detection(alerts, labels, list("ABCDE"))
    assert details["by_method"]["rule"]["confusion_matrix"] == [[2, 0], [2, 1]]
    assert details["by_method"]["statistical"]["confusion_matrix"] == [[1, 1], [1, 2]]
    assert details["by_anomaly_type"] == [
        {"anomaly_type": "x", "injected": 2, "rule": 1, "statistical": 2, "both": 1, "combined": 2},
        {"anomaly_type": "y", "injected": 1, "rule": 0, "statistical": 0, "both": 0, "combined": 0},
    ]
    assert details["statistical_increment"] == {"additional_tp": 1, "additional_fp": 1}
    assert details["false_positives"] == [
        {"record_id": "D", "findings": [{"method": "statistical", "reason": "exclusive false alarm"}]}
    ]
    assert details["false_negatives"] == [{"record_id": "C", "anomaly_type": "y"}]


def test_breakdown_distinguishes_pending_method_from_executed_method_without_alerts():
    alerts = pd.DataFrame(columns=["record_id", "method", "reason"])
    labels = pd.DataFrame({"record_id": ["A"]})

    _, details = evaluate_breakdown(alerts, labels, ["A", "B"], ("rule",))

    assert details["by_method"]["rule"]["TP"] == 0
    assert details["by_method"]["statistical"] is None
    assert details["statistical_increment"] is None
    assert details["by_anomaly_type"] == [
        {"anomaly_type": None, "injected": 1, "rule": 0, "statistical": None, "both": None, "combined": 0}
    ]


def test_breakdown_rejects_alerts_from_a_detector_that_did_not_run():
    alerts = pd.DataFrame({"record_id": ["A"], "method": ["statistical"], "reason": ["IQR"]})

    with pytest.raises(ValueError, match="method that did not run"):
        evaluate_breakdown(alerts, pd.DataFrame({"record_id": []}), ["A"], ("rule",))

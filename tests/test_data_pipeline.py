import pandas as pd
import pytest

from src.data_generation import generate_dataset
from src.preprocessing import preprocess_dataset, validate_dataset


def test_generated_dataset_is_reproducible():
    dataset_a, labels_a = generate_dataset(seed=123)
    dataset_b, labels_b = generate_dataset(seed=123)

    pd.testing.assert_frame_equal(dataset_a, dataset_b)
    pd.testing.assert_frame_equal(labels_a, labels_b)


def test_generator_creates_expected_anomalies_and_separate_labels():
    dataset, labels = generate_dataset(n_records=25, n_anomalies=8, seed=7)

    assert len(dataset) == 25
    assert len(labels) == 8
    assert dataset["record_id"].is_unique
    assert set(labels["anomaly_type"]) == {
        "turnout_over_capacity",
        "negative_vote_count",
        "vote_total_mismatch",
        "duplicate_station_id",
    }
    assert "anomaly_type" not in dataset.columns

    issues = validate_dataset(dataset)
    assert set(issues["issue_type"]) == {
        "turnout_over_capacity",
        "negative_count",
        "vote_total_mismatch",
        "duplicate_station_id",
    }
    detected_records = set(issues["record_id"])
    assert set(labels["record_id"]).issubset(detected_records)


def test_preprocessing_keeps_rows_and_strips_identifiers():
    dataset, _ = generate_dataset(n_records=10)
    dataset.loc[0, "station_id"] = "  ST-0001  "

    processed = preprocess_dataset(dataset)

    assert len(processed) == len(dataset)
    assert processed.loc[0, "station_id"] == "ST-0001"


def test_preprocessing_reports_missing_required_columns():
    with pytest.raises(ValueError, match="missing required columns"):
        preprocess_dataset(pd.DataFrame({"record_id": ["REC-0001"]}))


def test_validation_reports_missing_values_without_dropping_records():
    dataset, _ = generate_dataset(n_records=10)
    dataset.loc[0, "registered_voters"] = None

    issues = validate_dataset(dataset)

    assert len(issues.loc[issues["issue_type"] == "missing_value"]) == 1
    assert len(dataset) == 10


def test_generator_requires_enough_records_for_all_anomalies():
    with pytest.raises(ValueError, match="at least 4"):
        generate_dataset(n_records=3)


@pytest.mark.parametrize(
    ("n_records", "n_anomalies", "message"),
    [
        (10, 3, "at least 4"),
        (10, 11, "cannot exceed n_records"),
    ],
)
def test_generator_rejects_invalid_anomaly_counts(n_records, n_anomalies, message):
    with pytest.raises(ValueError, match=message):
        generate_dataset(n_records=n_records, n_anomalies=n_anomalies)


def test_generator_scales_to_larger_dataset_and_finds_all_labeled_anomalies():
    dataset, labels = generate_dataset(n_records=500, n_anomalies=25, seed=19)
    issues = validate_dataset(dataset)

    assert len(dataset) == 500
    assert len(labels) == 25
    assert set(labels["record_id"]).issubset(set(issues["record_id"]))

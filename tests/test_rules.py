import pandas as pd
import pytest

from src.data_generation import generate_dataset
from src.detection.rules import ALERT_COLUMNS, RULES, detect_rule_anomalies
from src.evaluate import evaluate_breakdown
from src.preprocessing import preprocess_dataset


def clean_records(count=6):
    """Coherent records: ballots sum to total_votes and turnout is below the census."""
    return pd.DataFrame(
        {
            "record_id": [f"REC-{i}" for i in range(count)],
            "station_id": [f"ST-{i}" for i in range(count)],
            "registered_voters": [500] * count,
            "votes_candidate_a": [200] * count,
            "votes_candidate_b": [100] * count,
            "votes_candidate_c": [50] * count,
            "blank_votes": [5] * count,
            "null_votes": [5] * count,
            "total_votes": [360] * count,
        }
    )


def alerted(records):
    alerts = detect_rule_anomalies(records)
    return alerts.groupby("record_id")["reason"].apply(list).to_dict()


def test_clean_records_raise_no_alerts_and_keep_schema():
    alerts = detect_rule_anomalies(clean_records())

    assert alerts.empty
    assert list(alerts.columns) == list(ALERT_COLUMNS)


def test_rule_codes_are_unique_and_documented():
    codes = [code for code, _, _ in RULES]

    assert len(codes) == len(set(codes))
    assert all(description for _, description, _ in RULES)


def test_negative_count_is_flagged_by_r2():
    records = clean_records()
    records.loc[2, "votes_candidate_c"] = -2

    found = alerted(records)

    assert set(found) == {"REC-2"}
    assert any(reason.startswith("R2") for reason in found["REC-2"])


def test_vote_total_mismatch_is_flagged_by_r3_only():
    records = clean_records()
    records.loc[1, "total_votes"] += 7

    found = alerted(records)

    assert set(found) == {"REC-1"}
    assert [reason[:2] for reason in found["REC-1"]] == ["R3"]


def test_turnout_over_capacity_is_flagged_by_r4():
    records = clean_records()
    records.loc[3, "registered_voters"] = 359  # 360 votes > 359 registered

    found = alerted(records)

    assert [reason[:2] for reason in found["REC-3"]] == ["R4"]


def test_turnout_equal_to_capacity_is_allowed():
    records = clean_records()
    records.loc[3, "registered_voters"] = 360

    assert detect_rule_anomalies(records).empty


def test_repeated_station_flags_only_later_copies():
    records = clean_records()
    records.loc[4, "station_id"] = "ST-0"

    alerts = detect_rule_anomalies(records)

    assert alerts["record_id"].tolist() == ["REC-4"]
    assert alerts["reason"].iloc[0].startswith("R5")


def test_missing_values_and_blank_identifiers_are_flagged_by_r1_without_crashing():
    records = clean_records()
    records["total_votes"] = records["total_votes"].astype("float")
    records.loc[0, "total_votes"] = None
    records.loc[5, "station_id"] = "  "

    found = alerted(records)

    assert set(found) == {"REC-0", "REC-5"}
    assert all(reason.startswith("R1") for reasons in found.values() for reason in reasons)


def test_one_record_can_trigger_several_rules():
    records = clean_records()
    records.loc[2, ["votes_candidate_c", "total_votes"]] = [-2, 600]

    reasons = alerted(records)["REC-2"]

    assert {reason[:2] for reason in reasons} == {"R2", "R3", "R4"}


def test_alerts_use_rule_method_and_do_not_mutate_input():
    records = clean_records()
    records.loc[1, "total_votes"] += 7
    before = records.copy()

    alerts = detect_rule_anomalies(records)

    assert alerts["method"].eq("rule").all()
    pd.testing.assert_frame_equal(records, before)


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda df: df.drop(columns="null_votes"), "missing required columns"),
        (lambda df: df.assign(record_id=["A", "A", "B", "C", "D", "E"]), "unique"),
        (lambda df: df.assign(record_id=["A", " ", "B", "C", "D", "E"]), "blank"),
    ],
)
def test_unusable_input_is_rejected(mutate, message):
    with pytest.raises(ValueError, match=message):
        detect_rule_anomalies(mutate(clean_records()))


def test_non_dataframe_is_rejected():
    with pytest.raises(TypeError):
        detect_rule_anomalies([1, 2, 3])


@pytest.mark.parametrize("seed", [1, 7, 19, 42, 100, 2026])
def test_rules_find_every_injected_anomaly_without_false_alarms(seed):
    dataset, labels = generate_dataset(n_records=500, n_anomalies=25, seed=seed)
    prepared = preprocess_dataset(dataset)

    alerts = detect_rule_anomalies(prepared)
    metrics, details = evaluate_breakdown(alerts, labels, prepared["record_id"], ["rule"])

    assert (metrics["TP"], metrics["FP"], metrics["FN"]) == (len(labels), 0, 0)
    assert all(row["rule"] == row["injected"] for row in details["by_anomaly_type"])


def test_rules_do_not_depend_on_ground_truth_columns():
    dataset, _ = generate_dataset(n_records=40, n_anomalies=8, seed=3)
    prepared = preprocess_dataset(dataset)
    prepared["participation_rate"] = prepared["total_votes"] / prepared["registered_voters"]

    with_rate = detect_rule_anomalies(prepared)
    without_rate = detect_rule_anomalies(prepared.drop(columns="participation_rate"))

    pd.testing.assert_frame_equal(with_rate, without_rate)

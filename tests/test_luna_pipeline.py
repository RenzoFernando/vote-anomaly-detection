import json

import pandas as pd

from src.analysis import summarize_data
from src.data_generation import BALLOT_COLUMNS, GROUND_TRUTH_PATH, RAW_DATA_PATH, generate_dataset
from src.detection.statistical import detect_statistical_anomalies
from src.main import run_pipeline
from src.preprocessing import preprocess_dataset, validate_dataset


def test_pipeline_exports_luna_results_for_diana_csvs(tmp_path):
    dataset = pd.read_csv(RAW_DATA_PATH, dtype={"record_id": "string", "station_id": "string"})
    labels = pd.read_csv(GROUND_TRUTH_PATH, dtype={"record_id": "string"})

    report = run_pipeline(dataset, labels, tmp_path)

    results = tmp_path / "results"
    assert json.loads((results / "metrics.json").read_text(encoding="utf-8")) == report
    prepared = pd.read_csv(
        results / "processed_dataset.csv",
        dtype={"record_id": "string", "station_id": "string"},
        float_precision="round_trip",
    )
    pd.testing.assert_frame_equal(prepared.drop(columns="participation_rate"), preprocess_dataset(dataset))
    assert prepared["participation_rate"].gt(1).sum() > 0
    assert report["stages"]["statistical"] == report["stages"]["analysis"] == "executed"
    assert report["analysis"] == summarize_data(prepared)
    assert report["analysis"]["record_count"] == len(dataset)

    alerts = pd.read_csv(results / "alerts.csv", keep_default_na=False)
    assert alerts.columns.tolist() == ["record_id", "method", "reason"]
    statistical = alerts.loc[alerts["method"].eq("statistical")]
    assert statistical.to_dict("records") == detect_statistical_anomalies(prepared).to_dict("records")
    flagged = set(statistical["record_id"])
    injected = set(labels["record_id"])
    scores = report["breakdown"]["by_method"]["statistical"]
    assert scores["TP"] == len(flagged & injected)
    assert scores["FP"] == len(flagged - injected)
    assert scores["FN"] == len(injected - flagged)
    assert (results / "report.html").is_file()


def test_pipeline_finds_coherent_low_turnout_with_real_iqr(tmp_path):
    dataset, labels = generate_dataset(n_records=240, n_anomalies=4, seed=19)
    row = dataset.index[-1]
    record_id = dataset.at[row, "record_id"]
    assert record_id not in set(labels["record_id"])
    dataset.loc[row, list(BALLOT_COLUMNS)] = [25, 0, 0, 0, 0]
    dataset.loc[row, ["registered_voters", "total_votes"]] = [500, 25]
    labels.loc[len(labels)] = [record_id, "low_turnout"]
    assert record_id not in set(validate_dataset(dataset)["record_id"])

    report = run_pipeline(dataset, labels, tmp_path)

    results = tmp_path / "results"
    alerts = pd.read_csv(results / "alerts.csv")
    statistical = alerts.loc[alerts["method"].eq("statistical")].set_index("record_id")
    assert "participation_rate 0.05 is below IQR lower bound" in statistical.at[record_id, "reason"]
    assert report["analysis"]["participation_rate"]["min"] == 0.05
    low_turnout = next(
        item for item in report["breakdown"]["by_anomaly_type"] if item["anomaly_type"] == "low_turnout"
    )
    assert low_turnout["statistical"] == low_turnout["injected"] == 1
    if report["stages"]["rule"] == "diana_validation_baseline":
        assert low_turnout["rule"] == 0
        assert report["breakdown"]["statistical_increment"]["additional_tp"] >= 1

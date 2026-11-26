import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pandas as pd
import pytest

from src.data_generation import (
    BALLOT_COLUMNS,
    GROUND_TRUTH_PATH,
    PROJECT_ROOT,
    RAW_DATA_PATH,
    generate_dataset,
)
from src.main import ALERT_COLUMNS, STAGES, run_pipeline


@pytest.fixture
def absent_team_modules(monkeypatch):
    for module_name, _ in STAGES.values():
        monkeypatch.setitem(sys.modules, module_name, None)


def test_diana_csvs_feed_the_partial_pipeline(tmp_path, absent_team_modules):
    dataset = pd.read_csv(RAW_DATA_PATH)
    labels = pd.read_csv(GROUND_TRUTH_PATH)

    report = run_pipeline(dataset, labels, tmp_path)

    results = tmp_path / "results"
    assert json.loads((results / "metrics.json").read_text(encoding="utf-8")) == report
    prepared = pd.read_csv(results / "processed_dataset.csv")
    alerts = pd.read_csv(results / "alerts.csv")
    assert report["mode"] == "partial"
    assert report["stages"] == {
        "rule": "diana_validation_baseline",
        "statistical": "pending",
        "analysis": "pending",
        "visualizations": "pending",
    }
    pd.testing.assert_frame_equal(prepared.drop(columns="participation_rate"), dataset)
    assert prepared["participation_rate"].max() > 1
    assert list(alerts.columns) == list(ALERT_COLUMNS)
    assert report["metrics"]["TP"] == len(labels)
    assert report["metrics"]["FP"] > 0
    assert report["metrics"]["FN"] == 0
    assert sum(map(sum, report["metrics"]["confusion_matrix"])) == len(dataset)
    assert report["breakdown"]["by_method"]["statistical"] is None
    html = (results / "report.html").read_text(encoding="utf-8")
    assert f"{len(dataset)} registros simulados" in html
    assert "Línea base de consistencia" in html
    assert "Matriz de confusión" in html
    assert "Diana" not in html
    false_positive = report["breakdown"]["false_positives"][0]
    assert false_positive["record_id"] in html


@pytest.mark.parametrize(("records", "anomalies", "seed"), [(24, 6, 7), (240, 4, 19), (240, 4, 42)])
def test_generated_data_runs_through_cli_reproducibly(tmp_path, records, anomalies, seed):
    def run_cli(output_dir):
        return subprocess.run(
            [
                sys.executable, "-m", "src.main", "--generate", "--records", str(records),
                "--anomalies", str(anomalies), "--seed", str(seed), "--output-dir", str(output_dir),
            ],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    first = tmp_path / "first"
    second = tmp_path / "second"
    assert f"{records} records" in run_cli(first).stdout
    run_cli(second)

    for name in ("processed_dataset.csv", "alerts.csv", "metrics.json", "report.html"):
        relative = Path("results") / name
        assert (first / relative).read_bytes() == (second / relative).read_bytes()


def test_one_run_composes_all_team_interfaces(tmp_path, monkeypatch):
    dataset, labels = generate_dataset(n_records=10, n_anomalies=4, seed=7)
    dataset.loc[0, "registered_voters"] = 0
    known = labels["record_id"].iloc[0]
    normal = dataset.loc[~dataset["record_id"].isin(labels["record_id"]), "record_id"].iloc[0]
    calls = []

    def check_prepared(prepared):
        assert "anomaly_type" not in prepared
        assert pd.isna(prepared["participation_rate"].iloc[0])

    def rules(prepared):
        check_prepared(prepared)
        calls.append("rule")
        return pd.DataFrame([(known, "rule", "known anomaly")], columns=ALERT_COLUMNS)

    def statistical(prepared):
        check_prepared(prepared)
        calls.append("statistical")
        return pd.DataFrame(
            [(known, "statistical", "same record"), (normal, "statistical", "rate < 0.1")],
            columns=ALERT_COLUMNS,
        )

    def summarize(prepared):
        check_prepared(prepared)
        calls.append("analysis")
        return {"record_count": len(prepared)}

    def visualize(prepared, alerts, ground_truth, output_dir, *, available_methods):
        check_prepared(prepared)
        calls.append("visualizations")
        assert tuple(available_methods) == ("rule", "statistical")
        pd.testing.assert_frame_equal(ground_truth, labels)
        assert list(alerts["record_id"]) == [known, known, normal]
        paths = [output_dir / f"figure {number}.txt" for number in range(1, 5)]
        for path in paths:
            path.write_text("figure fixture", encoding="utf-8")
        return paths

    for stage, function in zip(STAGES, (rules, statistical, summarize, visualize)):
        module_name, function_name = STAGES[stage]
        module = ModuleType(module_name)
        setattr(module, function_name, function)
        monkeypatch.setitem(sys.modules, module_name, module)

    report = run_pipeline(dataset, labels, tmp_path, require_complete=True)

    assert calls == ["rule", "statistical", "analysis", "visualizations"]
    assert report["mode"] == "complete"
    assert report["metrics"]["confusion_matrix"] == [[5, 1], [3, 1]]
    assert report["analysis"] == {"record_count": 10}
    assert len(report["figures"]) == 4
    assert all((tmp_path / figure).is_file() for figure in report["figures"])
    assert report["breakdown"]["statistical_increment"] == {"additional_tp": 0, "additional_fp": 1}
    html = (tmp_path / "results" / "report.html").read_text(encoding="utf-8")
    assert 'href="../figures/figure%201.txt"' in html
    assert "rate &lt; 0.1" in html


def test_low_turnout_with_coherent_counts_can_add_a_detection(
    tmp_path, monkeypatch, absent_team_modules
):
    dataset, labels = generate_dataset(n_records=240, n_anomalies=4, seed=19)
    candidates = dataset.loc[
        ~dataset["record_id"].isin(labels["record_id"])
        & ~dataset["station_id"].duplicated(keep=False)
    ]
    index = candidates.index[-1]
    record_id = dataset.at[index, "record_id"]
    dataset.loc[index, list(BALLOT_COLUMNS)] = [25, 0, 0, 0, 0]
    dataset.loc[index, ["registered_voters", "total_votes"]] = [500, 25]
    labels.loc[len(labels)] = [record_id, "low_turnout"]

    def statistical_double(prepared):
        assert "anomaly_type" not in prepared
        unusual_ids = prepared.loc[prepared["participation_rate"].lt(0.1), "record_id"]
        return pd.DataFrame(
            {"record_id": unusual_ids, "method": "statistical", "reason": "Low turnout test fixture"}
        )

    module_name, function_name = STAGES["statistical"]
    module = ModuleType(module_name)
    setattr(module, function_name, statistical_double)
    monkeypatch.setitem(sys.modules, module_name, module)

    report = run_pipeline(dataset, labels, tmp_path)

    details = report["breakdown"]
    assert details["by_method"]["rule"]["FN"] == 1
    assert details["statistical_increment"] == {"additional_tp": 1, "additional_fp": 0}
    assert report["metrics"]["FN"] == 0
    by_type = {row["anomaly_type"]: row for row in details["by_anomaly_type"]}
    assert by_type["low_turnout"] == {
        "anomaly_type": "low_turnout", "injected": 1,
        "rule": 0, "statistical": 1, "both": 0, "combined": 1,
    }


def test_complete_mode_reports_missing_modules(tmp_path, absent_team_modules):
    dataset, labels = generate_dataset()

    with pytest.raises(ValueError, match="Missing project stages: rule, statistical, analysis, visualizations"):
        run_pipeline(dataset, labels, tmp_path, require_complete=True)

    assert not (tmp_path / "results").exists()


def test_missing_dependency_inside_stage_is_not_treated_as_missing_stage(
    tmp_path, monkeypatch, absent_team_modules
):
    def import_broken_module(_):
        raise ModuleNotFoundError("Missing stage dependency", name="missing_dependency")

    monkeypatch.setattr("src.main.import_module", import_broken_module)
    dataset, labels = generate_dataset()

    with pytest.raises(ModuleNotFoundError, match="Missing stage dependency"):
        run_pipeline(dataset, labels, tmp_path)

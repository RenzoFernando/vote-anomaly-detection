import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import pandas as pd
import pytest

from src.data_generation import GROUND_TRUTH_PATH, PROJECT_ROOT, RAW_DATA_PATH, generate_dataset
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


def test_generated_data_runs_through_cli_reproducibly(tmp_path):
    def run_cli(output_dir):
        return subprocess.run(
            [
                sys.executable, "-m", "src.main", "--generate", "--records", "24",
                "--anomalies", "6", "--seed", "7", "--output-dir", str(output_dir),
            ],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    first = tmp_path / "first"
    second = tmp_path / "second"
    assert "24 records" in run_cli(first).stdout
    run_cli(second)

    for name in ("processed_dataset.csv", "alerts.csv", "metrics.json"):
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
            [(known, "statistical", "same record"), (normal, "statistical", "another record")],
            columns=ALERT_COLUMNS,
        )

    def summarize(prepared):
        check_prepared(prepared)
        calls.append("analysis")
        return {"record_count": len(prepared)}

    def visualize(prepared, alerts, ground_truth, output_dir):
        check_prepared(prepared)
        calls.append("visualizations")
        pd.testing.assert_frame_equal(ground_truth, labels)
        assert list(alerts["record_id"]) == [known, known, normal]
        paths = [output_dir / f"figure-{number}.txt" for number in range(1, 5)]
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

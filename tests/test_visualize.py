from pathlib import Path

import sys

import pandas as pd
import pytest

from src.data_generation import generate_dataset
from src.detection.rules import detect_rule_anomalies
from src.detection.statistical import detect_statistical_anomalies
from src.main import run_pipeline
from src.preprocessing import preprocess_dataset
from src import visualize
from src.visualize import FIGURE_FILES, _iqr_fences, _status, create_visualizations

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def prepare(records=200, anomalies=10, seed=42):
    dataset, labels = generate_dataset(n_records=records, n_anomalies=anomalies, seed=seed)
    prepared = preprocess_dataset(dataset)
    prepared["participation_rate"] = prepared["total_votes"] / prepared["registered_voters"]
    alerts = pd.concat(
        [detect_rule_anomalies(prepared), detect_statistical_anomalies(prepared)], ignore_index=True
    )
    return prepared, alerts, labels


def assert_valid_figures(paths, output_dir):
    assert [Path(path).name for path in paths] == list(FIGURE_FILES)
    assert len(set(paths)) == 4
    for path in paths:
        assert Path(path).parent == output_dir
        content = Path(path).read_bytes()
        assert content.startswith(PNG_SIGNATURE)
        assert len(content) > 5_000  # an empty canvas is far smaller


def test_creates_four_distinct_valid_png_files(tmp_path):
    prepared, alerts, labels = prepare()

    paths = create_visualizations(prepared, alerts, labels, tmp_path)

    assert_valid_figures(paths, tmp_path)


def test_creates_missing_output_directory(tmp_path):
    prepared, alerts, labels = prepare(records=50, anomalies=4)
    target = tmp_path / "nested" / "figures"

    paths = create_visualizations(prepared, alerts, labels, target)

    assert_valid_figures(paths, target)


def test_does_not_modify_its_inputs(tmp_path):
    prepared, alerts, labels = prepare()
    snapshots = [frame.copy() for frame in (prepared, alerts, labels)]

    create_visualizations(prepared, alerts, labels, tmp_path)

    for frame, snapshot in zip((prepared, alerts, labels), snapshots):
        pd.testing.assert_frame_equal(frame, snapshot)


def test_runs_without_alerts_and_with_a_missed_anomaly(tmp_path):
    prepared, _, labels = prepare()
    no_alerts = pd.DataFrame(columns=["record_id", "method", "reason"])

    paths = create_visualizations(prepared, no_alerts, labels, tmp_path)

    assert_valid_figures(paths, tmp_path)


def test_runs_with_false_alarms_and_unlabelled_types(tmp_path):
    prepared, alerts, labels = prepare()
    normal = prepared.loc[~prepared["record_id"].isin(labels["record_id"]), "record_id"].iloc[0]
    alerts.loc[len(alerts)] = [normal, "statistical", "test false alarm"]

    paths = create_visualizations(prepared, alerts, labels[["record_id"]], tmp_path)

    assert_valid_figures(paths, tmp_path)


def test_runs_with_zero_registered_voters(tmp_path):
    prepared, alerts, labels = prepare(records=50, anomalies=4)
    prepared.loc[0, "registered_voters"] = 0
    prepared.loc[0, "participation_rate"] = float("nan")

    assert_valid_figures(create_visualizations(prepared, alerts, labels, tmp_path), tmp_path)


def test_status_classifies_all_four_outcomes():
    prepared = pd.DataFrame({"record_id": ["a", "b", "c", "d"]})
    alerts = pd.DataFrame({"record_id": ["a", "c"], "method": "rule", "reason": "x"})
    labels = pd.DataFrame({"record_id": ["a", "b"]})

    status = _status(prepared, alerts, labels)

    assert status.tolist() == ["detected", "missed", "false_alarm", "normal"]


def test_iqr_fences_match_the_statistical_detector():
    prepared, _, _ = prepare(records=300, anomalies=12, seed=5)
    rates = prepared["participation_rate"]
    low, high = _iqr_fences(rates)
    flagged = set(detect_statistical_anomalies(prepared)["record_id"])

    outside = prepared.loc[(rates < low) | (rates > high), "record_id"]

    assert set(outside) == flagged
    assert _iqr_fences(pd.Series([0.5, 0.6, 0.7])) is None


@pytest.mark.parametrize(
    "bad_args, message",
    [
        (lambda p, a, l: (p.drop(columns="record_id"), a, l), "record_id"),
        (lambda p, a, l: (p, a, l.drop(columns="record_id")), "record_id"),
        (lambda p, a, l: (p, a.drop(columns="method"), l), "method"),
        (lambda p, a, l: (p, a.drop(columns="reason"), l), "reason"),
    ],
)
def test_rejects_missing_columns(tmp_path, bad_args, message):
    prepared, alerts, labels = prepare(records=50, anomalies=4)

    with pytest.raises(ValueError, match=message):
        create_visualizations(*bad_args(prepared, alerts, labels), tmp_path)


def test_full_pipeline_runs_in_complete_mode_with_real_stages(tmp_path):
    dataset, labels = generate_dataset(n_records=300, n_anomalies=15, seed=11)

    report = run_pipeline(dataset, labels, tmp_path, require_complete=True)

    assert report["mode"] == "complete"
    assert [Path(path).name for path in report["figures"]] == list(FIGURE_FILES)
    assert all((tmp_path / path).is_file() for path in report["figures"])
    assert report["metrics"]["recall"] == 1.0
    assert report["metrics"]["FP"] == 0
    html = (tmp_path / "results" / "report.html").read_text(encoding="utf-8")
    assert "participation distribution" in html


def test_partial_pipeline_omits_pending_iqr_from_figures(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "src.detection.statistical", None)
    dataset, labels = generate_dataset(n_records=50, n_anomalies=4)
    plot_labels = {}
    save = visualize._save

    def capture_labels(figure, path):
        plot_labels[path.name] = [
            label for axis in figure.axes for label in axis.get_legend_handles_labels()[1]
        ]
        return save(figure, path)

    monkeypatch.setattr(visualize, "_save", capture_labels)
    report = run_pipeline(dataset, labels, tmp_path)

    assert report["stages"]["statistical"] == "pending"
    assert report["breakdown"]["by_method"]["statistical"] is None
    assert all("IQR" not in label for labels in plot_labels.values() for label in labels)
    assert "Reglas" in plot_labels["confusion_and_metrics.png"]

"""Run detection and evaluation on simulated election records."""

import argparse
import json
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.data_generation import (
    DEFAULT_RECORDS,
    GROUND_TRUTH_PATH,
    PROJECT_ROOT,
    RAW_DATA_PATH,
    generate_dataset,
)
from src.evaluate import DETECTION_METHODS, evaluate_breakdown
from src.preprocessing import preprocess_dataset, validate_dataset
from src.report import render_report


ALERT_COLUMNS = ("record_id", "method", "reason")
STAGES = {
    "rule": ("src.detection.rules", "detect_rule_anomalies"),
    "statistical": ("src.detection.statistical", "detect_statistical_anomalies"),
    "analysis": ("src.analysis", "summarize_data"),
    "visualizations": ("src.visualize", "create_visualizations"),
}


def _load_stage(module_name: str, function_name: str):
    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name != module_name:
            raise
        return None
    return getattr(module, function_name)


def _validation_alerts(prepared: pd.DataFrame) -> pd.DataFrame:
    issues = validate_dataset(prepared)
    return issues.rename(columns={"message": "reason"}).assign(method="rule")


def run_pipeline(
    dataset: pd.DataFrame,
    ground_truth: pd.DataFrame,
    output_dir: Path,
    *,
    require_complete: bool = False,
) -> dict:
    """Run the available stages and export a report of what actually ran."""
    stages = {name: _load_stage(*target) for name, target in STAGES.items()}
    missing = [name for name, stage in stages.items() if stage is None]
    if require_complete and missing:
        raise ValueError(f"Missing project stages: {', '.join(missing)}")

    prepared = preprocess_dataset(dataset)
    registered = prepared["registered_voters"]
    prepared["participation_rate"] = (
        prepared["total_votes"] / registered.where(registered.gt(0))
    )

    status = {name: "pending" if stage is None else "executed" for name, stage in stages.items()}
    if stages["rule"] is None:
        stages["rule"] = _validation_alerts
        status["rule"] = "diana_validation_baseline"

    alert_frames = []
    available_methods = []
    for method in DETECTION_METHODS:
        detector = stages[method]
        if detector is None:
            continue
        detected = detector(prepared.copy())
        if not isinstance(detected, pd.DataFrame) or not set(ALERT_COLUMNS).issubset(detected):
            raise ValueError(
                f"The {method} detector must return a DataFrame with {ALERT_COLUMNS}."
            )
        if not detected["method"].eq(method).fillna(False).all():
            raise ValueError(f"The {method} detector returned an invalid method value.")
        detected = detected.loc[:, list(ALERT_COLUMNS)].copy()
        detected["record_id"] = detected["record_id"].astype("string").str.strip()
        alert_frames.append(detected)
        available_methods.append(method)

    alerts = pd.concat(alert_frames, ignore_index=True)
    metrics, breakdown = evaluate_breakdown(
        alerts, ground_truth, prepared["record_id"], available_methods
    )
    summarize = stages["analysis"]
    report = {
        "mode": "partial" if missing else "complete",
        "records": len(prepared),
        "alert_rows": len(alerts),
        "stages": status,
        "metrics": metrics,
        "breakdown": breakdown,
        "analysis": summarize(prepared.copy()) if summarize is not None else None,
        "figures": [],
    }

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir) as temp_dir:
        staging = Path(temp_dir)
        visualize = stages["visualizations"]
        if visualize is not None:
            figures_dir = staging / "figures"
            figures_dir.mkdir()
            figure_paths = []
            paths = visualize(prepared.copy(), alerts.copy(), ground_truth.copy(), figures_dir)
            for path in paths:
                figure_path = (figures_dir / Path(path)).resolve()
                if not figure_path.is_relative_to(figures_dir) or not figure_path.is_file():
                    raise ValueError(
                        "Visualizations must return paths to files in the figures directory."
                    )
                figure_paths.append(figure_path.relative_to(staging).as_posix())
            if len(figure_paths) != 4 or len(set(figure_paths)) != 4:
                raise ValueError("The visualization stage must return four distinct figure files.")
            report["figures"] = figure_paths

        results = staging / "results"
        results.mkdir()
        prepared.to_csv(results / "processed_dataset.csv", index=False)
        alerts.to_csv(results / "alerts.csv", index=False)
        (results / "report.html").write_text(render_report(report), encoding="utf-8")
        (results / "metrics.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        for relative_path in [
            *report["figures"],
            "results/processed_dataset.csv",
            "results/alerts.csv",
            "results/report.html",
            "results/metrics.json",
        ]:
            destination = output_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            (staging / relative_path).replace(destination)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, help="simulated dataset CSV")
    parser.add_argument("--labels", type=Path, help="positive-only anomaly labels CSV")
    parser.add_argument("--generate", action="store_true", help="generate simulated data in memory")
    parser.add_argument("--records", type=int, help="number of records to generate")
    parser.add_argument("--anomalies", type=int, help="number of anomalies to generate")
    parser.add_argument("--seed", type=int, help="random seed for generated data")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "outputs")
    parser.add_argument("--require-complete", action="store_true", help="require all project stages")
    args = parser.parse_args()
    if args.generate and (args.dataset is not None or args.labels is not None):
        parser.error("--generate cannot be combined with --dataset or --labels")
    generation_options = (args.records, args.anomalies, args.seed)
    if not args.generate and generation_options != (None, None, None):
        parser.error("--records, --anomalies and --seed require --generate")

    try:
        if args.generate:
            dataset, labels = generate_dataset(
                n_records=DEFAULT_RECORDS if args.records is None else args.records,
                n_anomalies=args.anomalies,
                seed=42 if args.seed is None else args.seed,
            )
        else:
            dataset = pd.read_csv(
                args.dataset or RAW_DATA_PATH,
                dtype={"record_id": "string", "station_id": "string"},
            )
            labels = pd.read_csv(args.labels or GROUND_TRUTH_PATH, dtype={"record_id": "string"})
        report = run_pipeline(dataset, labels, args.output_dir, require_complete=args.require_complete)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"VoteAnomaly: {exc}\n")

    print(
        f"VoteAnomaly ({report['mode']} run) | "
        f"{report['records']} records | {report['alert_rows']} alerts"
    )
    for stage, status in report["stages"].items():
        print(f"  {stage}: {status}")
    metrics = report["metrics"]
    print(f"TP={metrics['TP']}  FP={metrics['FP']}  FN={metrics['FN']}  TN={metrics['TN']}")
    print(f"Precision={metrics['precision']:.4f}  Recall={metrics['recall']:.4f}  F1={metrics['f1']:.4f}")
    print(f"Results: {args.output_dir / 'results'}")
    print(f"HTML report: {args.output_dir / 'results' / 'report.html'}")


if __name__ == "__main__":
    main()

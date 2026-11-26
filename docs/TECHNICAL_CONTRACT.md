# VoteAnomaly integration contract

## Simulated inputs and evaluation

The CSV schema follows `src.data_generation` and `src.preprocessing`. Each
record has a unique `record_id`. The `station_id` can repeat because duplicate
station identifiers are one of the injected anomalies. The ballot columns
include candidates A, B and C, blank ballots and null ballots. The pipeline
adds `participation_rate = total_votes / registered_voters` for positive
denominators and leaves the rate missing otherwise. Out-of-range results
remain available to the detectors.

`data/ground_truth/anomaly_labels.csv` lists only injected anomalies, with
`record_id` and `anomaly_type`. Unlisted dataset records count as negatives.
Use `evaluate_detection(alerts, ground_truth, prepared["record_id"])` to
evaluate the union of alerted IDs. Repeated alerts are counted once in the
metrics and remain visible in the alerts CSV. Unknown IDs and duplicate
dataset or reference IDs cause evaluation to fail.

`metrics.json` records TP, FP, FN, TN, precision, recall and F1. Its
`confusion_matrix` is `[[TN, FP], [FN, TP]]`, with reference classes in the
rows and predicted classes in the columns, in negative-to-positive order.
Ratios with zero denominators are reported as zero.

The `breakdown` records scores for each executed detector, counts by
injected anomaly type, and the IDs of false positives and false negatives.
The `combined` column counts the union of alerted records. The `both`
column counts the intersection. Pending detectors and comparisons involving
them use `null`. A detector that ran and found nothing contributes zero
alerts. `statistical_increment` counts the true and false positives among
records flagged only by the statistical detector.

`outputs/results/report.html` renders these results without online
dependencies. If visualizations ran, it links to the four current files
under `outputs/figures/`. Keep the two folders together when sharing a
complete run so those links work.

## Interfaces for the remaining modules

| Module | Function | Return value |
| --- | --- | --- |
| `src/detection/rules.py` | `detect_rule_anomalies(prepared)` | Alert DataFrame with `method="rule"` |
| `src/detection/statistical.py` | `detect_statistical_anomalies(prepared)` | Alert DataFrame with `method="statistical"` |
| `src/analysis.py` | `summarize_data(prepared)` | Descriptive results as JSON-compatible Python values. Use `None` for undefined statistics. |
| `src/visualize.py` | `create_visualizations(prepared, alerts, ground_truth, output_dir)` | Iterable of four distinct paths to files saved inside `output_dir` |

Each detector returns `record_id`, `method` and `reason`, including those
columns for an empty result. Use `record_id` to highlight alerts and to
evaluate the confusion matrix in the visualizations. The detectors and
exploratory analysis receive only the prepared election records. The
visualization stage also receives the labels for the confusion matrix.

## Partial runs

When the rules module is absent, the pipeline converts Diana's
`validate_dataset` findings to alerts and records their source as
`diana_validation_baseline`. An original record sharing a duplicated
`station_id` can trigger this validation and count as a false positive
against the injected labels. Other absent stages are marked `pending`.

Use `python -m src.main --require-complete` for the integrated run. It fails
if any listed module is absent. A module that exists but fails to import
also surfaces its error. The `figures` list in `metrics.json` identifies
the files produced by the current run.

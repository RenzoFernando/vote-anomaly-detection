"""Create the four project figures from one pipeline run.

Entry point: ``create_visualizations(prepared, alerts, ground_truth, output_dir)``
returns four distinct PNG paths inside ``output_dir`` (the contract used by
``src.main``). Ground-truth labels are used only to colour and score results;
they never influence detection.
"""

from collections.abc import Iterable
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless backend: no display needed for tests or CI

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src._participation import participation_rates  # noqa: E402
from src.evaluate import DETECTION_METHODS, evaluate_breakdown  # noqa: E402


FIGURE_FILES = (
    "participation_distribution.png",
    "registered_vs_votes.png",
    "detection_by_anomaly_type.png",
    "confusion_and_metrics.png",
)
COLORS = {
    "normal": "#9aa5b1",
    "detected": "#2e7d32",   # injected and alerted (true positive)
    "missed": "#c62828",     # injected, not alerted (false negative)
    "false_alarm": "#ef6c00",  # alerted but not injected (false positive)
    "rule": "#1565c0",
    "statistical": "#6a1b9a",
}
METHOD_LABELS = {"rule": "Reglas", "statistical": "IQR"}
ANOMALY_LABELS = {
    "duplicate_station_id": "Mesa duplicada",
    "negative_vote_count": "Conteo negativo",
    "turnout_over_capacity": "Votos > censo",
    "vote_total_mismatch": "Suma inconsistente",
    "low_turnout": "Baja participación",
}
DPI = 130


def _status(prepared: pd.DataFrame, alerts: pd.DataFrame, ground_truth: pd.DataFrame) -> pd.Series:
    """Classify every record as normal / detected / missed / false_alarm."""
    ids = prepared["record_id"].astype("string").str.strip()
    alerted = set(alerts["record_id"].astype("string").str.strip()) if len(alerts) else set()
    injected = set(ground_truth["record_id"].astype("string").str.strip())
    status = pd.Series("normal", index=prepared.index, dtype="object")
    is_alerted = ids.isin(alerted)
    is_injected = ids.isin(injected)
    status[is_alerted & is_injected] = "detected"
    status[~is_alerted & is_injected] = "missed"
    status[is_alerted & ~is_injected] = "false_alarm"
    return status


def _legend_label(status_name: str, count: int) -> str:
    names = {
        "normal": "Normal",
        "detected": "Anomalía detectada",
        "missed": "Anomalía no detectada",
        "false_alarm": "Falsa alarma",
    }
    return f"{names[status_name]} ({count})"


def _save(fig: plt.Figure, path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, metadata={"Software": None})
    plt.close(fig)
    return path


def _iqr_fences(rates: pd.Series) -> tuple[float, float] | None:
    """Same Tukey fences as the statistical detector (>= 4 finite rates)."""
    finite = rates[np.isfinite(rates)]
    if len(finite) < 4:
        return None
    q1, q3 = finite.quantile([0.25, 0.75], interpolation="linear")
    iqr = q3 - q1
    return float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr)


def plot_participation_distribution(prepared, status, path: Path, *, include_iqr: bool) -> Path:
    """Fig. 1: histogram of participation with IQR fences and 100% capacity line."""
    rates = participation_rates(prepared)
    finite = np.isfinite(rates)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    if finite.any():
        bins = np.histogram_bin_edges(rates[finite], bins=30)
        groups = {k: rates[finite & status.eq(k)] for k in ("normal", "detected", "missed", "false_alarm")}
        ax.hist(
            list(groups.values()), bins=bins, stacked=True,
            color=[COLORS[k] for k in groups],
            label=[_legend_label(k, int(len(v))) for k, v in groups.items()],
        )
    fences = _iqr_fences(rates) if include_iqr else None
    if fences:
        for value, name in zip(fences, ("Límite inferior IQR", "Límite superior IQR")):
            ax.axvline(value, color=COLORS["statistical"], linestyle="--", linewidth=1.2, label=name)
    ax.axvline(1.0, color="black", linestyle=":", linewidth=1.2, label="100 % del censo")
    ax.set_title("Distribución de la participación por mesa")
    ax.set_xlabel("Participación (votos totales / votantes registrados)")
    ax.set_ylabel("Número de mesas")
    ax.legend(fontsize=8)
    return _save(fig, path)


def plot_registered_vs_votes(prepared, status, path: Path) -> Path:
    """Fig. 2: registered voters vs votes counted; points above y=x exceed capacity."""
    x = pd.to_numeric(prepared["registered_voters"], errors="coerce")
    y = pd.to_numeric(prepared["total_votes"], errors="coerce")
    fig, ax = plt.subplots(figsize=(7, 6))
    for key, size, z in (("normal", 14, 1), ("false_alarm", 40, 3), ("missed", 55, 4), ("detected", 40, 5)):
        mask = status.eq(key)
        ax.scatter(x[mask], y[mask], s=size, color=COLORS[key], alpha=0.85 if key != "normal" else 0.5,
                   label=_legend_label(key, int(mask.sum())), zorder=z)
    upper = np.nanmax([x.max(), y.max()]) if x.notna().any() and y.notna().any() else 1
    ax.plot([0, upper], [0, upper], color="black", linestyle=":", linewidth=1.2, label="Capacidad (votos = censo)")
    ax.set_title("Votantes registrados vs. votos contados")
    ax.set_xlabel("Votantes registrados")
    ax.set_ylabel("Votos totales")
    ax.legend(fontsize=8, loc="upper left")
    return _save(fig, path)


def plot_detection_by_anomaly_type(details, path: Path) -> Path:
    """Fig. 3: for each injected anomaly type, how many each detector caught."""
    rows = details["by_anomaly_type"]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    if rows:
        labels = [ANOMALY_LABELS.get(r["anomaly_type"], r["anomaly_type"] or "Sin tipo") for r in rows]
        series = [("Inyectadas", [r["injected"] for r in rows], "#455a64")]
        series += [
            (f"Detectadas por {METHOD_LABELS[m]}", [r[m] for r in rows], COLORS[m])
            for m, scores in details["by_method"].items() if scores is not None
        ]
        positions = np.arange(len(rows))
        width = 0.8 / len(series)
        for i, (name, values, color) in enumerate(series):
            bars = ax.bar(positions + i * width, values, width, label=name, color=color)
            ax.bar_label(bars, fontsize=8, padding=2)
        ax.set_xticks(positions + width * (len(series) - 1) / 2, labels, rotation=15, ha="right")
        ax.legend(fontsize=8)
    else:
        ax.text(0.5, 0.5, "No hay anomalías inyectadas", ha="center", va="center", transform=ax.transAxes)
    ax.set_title("Cobertura de detección por tipo de anomalía")
    ax.set_ylabel("Número de registros")
    return _save(fig, path)


def plot_confusion_and_metrics(combined, details, path: Path) -> Path:
    """Fig. 4: combined confusion matrix and precision/recall/F1 per detector."""
    fig, (ax_matrix, ax_bars) = plt.subplots(1, 2, figsize=(11, 4.5), gridspec_kw={"width_ratios": [1, 1.3]})

    matrix = np.array(combined["confusion_matrix"])
    ax_matrix.imshow(matrix, cmap="Blues")
    for (row, col), value in np.ndenumerate(matrix):
        ax_matrix.text(col, row, str(value), ha="center", va="center", fontsize=14,
                       color="white" if value > matrix.max() / 2 else "black")
    ax_matrix.set_xticks([0, 1], ["Normal", "Alerta"])
    ax_matrix.set_yticks([0, 1], ["Normal", "Anomalía"])
    ax_matrix.set_xlabel("Predicción")
    ax_matrix.set_ylabel("Realidad")
    ax_matrix.set_title("Matriz de confusión (combinada)")

    scored = [("Combinada", combined)] + [
        (METHOD_LABELS[m], scores)
        for m, scores in details["by_method"].items() if scores is not None
    ]
    metrics = ("precision", "recall", "f1")
    positions = np.arange(len(metrics))
    width = 0.8 / len(scored)
    for i, (name, scores) in enumerate(scored):
        bars = ax_bars.bar(positions + i * width, [scores[m] for m in metrics], width, label=name)
        ax_bars.bar_label(bars, fmt="%.2f", fontsize=8, padding=2)
    ax_bars.set_xticks(positions + width * (len(scored) - 1) / 2, ["Precisión", "Recall", "F1"])
    ax_bars.set_ylim(0, 1.3)
    ax_bars.set_title("Métricas por detector")
    ax_bars.legend(fontsize=8, loc="upper center", ncol=len(scored))
    return _save(fig, path)


def create_visualizations(
    prepared: pd.DataFrame,
    alerts: pd.DataFrame,
    ground_truth: pd.DataFrame,
    output_dir: Path,
    *,
    available_methods: Iterable[str] = DETECTION_METHODS,
) -> list[Path]:
    """Write the four figures to ``output_dir`` and return their paths in order.

    Only executed detectors appear. A detector that ran without raising alerts
    is drawn as zero.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if "record_id" not in prepared or "record_id" not in ground_truth:
        raise ValueError("Prepared records and ground truth require a record_id column.")
    if not {"record_id", "method", "reason"}.issubset(alerts.columns):
        raise ValueError("Alerts require record_id, method and reason columns.")

    combined, details = evaluate_breakdown(alerts, ground_truth, prepared["record_id"], available_methods)
    status = _status(prepared, alerts, ground_truth)
    paths = [output_dir / name for name in FIGURE_FILES]
    plot_participation_distribution(
        prepared, status, paths[0], include_iqr=details["by_method"]["statistical"] is not None
    )
    plot_registered_vs_votes(prepared, status, paths[1])
    plot_detection_by_anomaly_type(details, paths[2])
    plot_confusion_and_metrics(combined, details, paths[3])
    return paths

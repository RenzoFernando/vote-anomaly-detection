"""Render the pipeline results as a standalone HTML report."""

from html import escape
from pathlib import Path
from string import Template
from urllib.parse import quote


METHOD_NAMES = {"rule": "Reglas", "statistical": "IQR"}
STAGE_NAMES = {"rule": "reglas", "statistical": "IQR", "analysis": "análisis", "visualizations": "gráficos"}
STATUS_NAMES = {
    "diana_validation_baseline": "Línea base de consistencia",
    "executed": "Ejecutado",
    "pending": "Pendiente",
}
ANOMALY_NAMES = {
    "duplicate_station_id": "Identificador de mesa duplicado",
    "negative_vote_count": "Conteo negativo",
    "turnout_over_capacity": "Participación superior al censo",
    "vote_total_mismatch": "Suma de votos inconsistente",
    "low_turnout": "Participación inusualmente baja",
}
METRIC_NAMES = {"precision": "Precisión", "recall": "Recall", "f1": "F1"}


def _anomaly_name(kind: str | None) -> str:
    return escape(ANOMALY_NAMES.get(kind, kind or "Sin tipo"))


def _metric_row(label: str, metrics: dict | None) -> str:
    if metrics is None:
        return f'<tr><th scope="row">{label}</th><td class="muted" colspan="7">Pendiente</td></tr>'
    cells = "".join(f"<td>{metrics[key]:.4f}</td>" for key in METRIC_NAMES)
    cells += "".join(f"<td>{metrics[key]}</td>" for key in ("TP", "FP", "FN", "TN"))
    return f'<tr><th scope="row">{label}</th>{cells}</tr>'


def _examples(items: list[dict], *, positive: bool) -> str:
    if not items:
        return '<p class="muted">Ninguno en esta ejecución.</p>'
    examples = []
    for item in items[:5]:
        if positive:
            description = "<br>".join(
                f"{METHOD_NAMES[finding['method']]} · {escape(finding['reason'])}"
                for finding in item["findings"]
            ) or "Motivo sin especificar"
        else:
            description = _anomaly_name(item["anomaly_type"])
        examples.append(f"<li><code>{escape(item['record_id'])}</code><div>{description}</div></li>")
    remainder = (
        f'<p class="muted">Se muestran 5 de {len(items)}. El detalle está en metrics.json.</p>'
        if len(items) > 5 else ""
    )
    return f"<ul class=examples>{''.join(examples)}</ul>{remainder}"


def render_report(report: dict) -> str:
    metrics = report["metrics"]
    details = report["breakdown"]
    mode = "parcial" if report["mode"] == "partial" else "completa"
    tn, fp = metrics["confusion_matrix"][0]
    fn, tp = metrics["confusion_matrix"][1]
    kpis = {name: f"{metrics[key]:.4f}" for key, name in METRIC_NAMES.items()}
    kpis["Registros alertados"] = str(tp + fp)
    cards = "".join(f"<div><dt>{name}</dt><dd>{value}</dd></div>" for name, value in kpis.items())

    comparison = _metric_row("Combinada", metrics) + "".join(
        _metric_row(label, details["by_method"][method]) for method, label in METHOD_NAMES.items()
    )
    coverage = []
    for row in details["by_anomaly_type"]:
        cells = "".join(
            f'<td>{row[key] if row[key] is not None else "—"}</td>'
            for key in ("injected", "rule", "statistical", "both", "combined")
        )
        coverage.append(f'<tr><th scope="row">{_anomaly_name(row["anomaly_type"])}</th>{cells}</tr>')
    coverage_rows = "".join(coverage) or '<tr><td colspan="6">No hay anomalías inyectadas.</td></tr>'

    increment = details["statistical_increment"]
    if increment is None:
        contribution = "El aporte adicional del IQR se calcula cuando se ejecutan ambos detectores."
    else:
        contribution = (
            f"Aporte exclusivo del IQR: <strong>{increment['additional_tp']}</strong> anomalías "
            f"detectadas y <strong>{increment['additional_fp']}</strong> falsos positivos."
        )

    terminal_values = {
        "modo": mode,
        **{STAGE_NAMES[stage]: STATUS_NAMES[state] for stage, state in report["stages"].items()},
        "alertas emitidas": report["alert_rows"],
    }
    terminal = "".join(
        f"<div><dt>{key}</dt><dd>{value}</dd></div>" for key, value in terminal_values.items()
    )
    figures = ""
    if report["figures"]:
        links = []
        for path in report["figures"]:
            name = Path(path).stem.replace("_", " ").replace("-", " ")
            links.append(f'<li><a href="../{quote(path)}">{escape(name)}</a></li>')
        figures = (
            f'<section><h2>Gráficos de esta ejecución</h2>'
            f'<ul class="links">{"".join(links)}</ul></section>'
        )

    template = Template(Path(__file__).with_name("report_template.html").read_text(encoding="utf-8"))
    return template.substitute(
        mode=mode, records=report["records"], cards=cards, terminal=terminal,
        tn=tn, fp=fp, fn=fn, tp=tp, comparison=comparison, coverage=coverage_rows,
        contribution=contribution, figures=figures,
        false_positives=_examples(details["false_positives"], positive=True),
        false_negatives=_examples(details["false_negatives"], positive=False),
    )

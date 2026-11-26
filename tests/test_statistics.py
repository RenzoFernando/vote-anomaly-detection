import math

import pandas as pd
import pytest

from src.detection.statistical import detect_statistical_anomalies


EXPECTED_COLUMNS = ["record_id", "method", "reason"]


def prepared(rates, ids=None):
    if ids is None:
        ids = [f"R{index}" for index in range(len(rates))]
    return pd.DataFrame({"record_id": ids, "participation_rate": rates})


@pytest.mark.parametrize(
    "rates",
    [[], [0.5, 0.6, 0.65, 0.7], [0.5, 0.6, 3.0, None, math.inf, "invalid"], [1.25] * 5],
)
def test_no_alerts_keep_schema(rates):
    alerts = detect_statistical_anomalies(prepared(rates))

    assert alerts.empty
    assert list(alerts.columns) == EXPECTED_COLUMNS


def test_flags_both_outliers_but_keeps_exact_fences_inside():
    lower_outlier = math.nextafter(0.0, -math.inf)
    upper_outlier = math.nextafter(1.0, math.inf)
    data = prepared([upper_outlier, 1.0, 0.625, 0.625, 0.5, 0.375, 0.375, 0.0, lower_outlier])

    alerts = detect_statistical_anomalies(data)

    # Q1 = 0.375 and Q3 = 0.625 give fences of 0 and 1.
    assert alerts.to_dict("records") == [
        {
            "record_id": "R0",
            "method": "statistical",
            "reason": f"participation_rate {upper_outlier} is above IQR upper bound 1.0.",
        },
        {
            "record_id": "R8",
            "method": "statistical",
            "reason": f"participation_rate {lower_outlier} is below IQR lower bound 0.0.",
        },
    ]


def test_zero_iqr_flags_rates_different_from_tied_quartiles():
    data = prepared([0.55, *([0.625] * 6), 0.7])

    alerts = detect_statistical_anomalies(data)

    assert alerts["record_id"].tolist() == ["R0", "R7"]
    assert alerts["reason"].str.endswith("0.625.").all()


def test_uses_numeric_strings_and_excludes_missing_infinite_and_invalid_rates():
    data = prepared(["0.6", 0.6, 0.6, 0.6, "1.3", math.nan, math.inf, "-inf", "bad", True, 1j])

    alerts = detect_statistical_anomalies(data)

    assert alerts["record_id"].tolist() == ["R4"]
    assert alerts.iloc[0]["reason"] == "participation_rate 1.3 is above IQR upper bound 0.6."


@pytest.mark.parametrize(
    ("ids", "message"),
    [(["R0", " R0 "], "unique"), ([None, "R1"], "missing or blank"), (["  ", "R1"], "missing or blank")],
)
def test_rejects_duplicate_or_unusable_record_ids(ids, message):
    with pytest.raises(ValueError, match=message):
        detect_statistical_anomalies(prepared([0.6, 1.2], ids=ids))


@pytest.mark.parametrize("column", ["record_id", "participation_rate"])
@pytest.mark.parametrize("duplicate", [False, True])
def test_rejects_missing_or_duplicate_required_columns(column, duplicate):
    data = prepared([0.6])
    data = pd.concat([data, data[[column]]], axis=1) if duplicate else data.drop(columns=column)

    with pytest.raises(ValueError, match=column):
        detect_statistical_anomalies(data)


def test_rejects_non_dataframe():
    with pytest.raises(TypeError, match="DataFrame"):
        detect_statistical_anomalies({"record_id": [], "participation_rate": []})


def test_detector_preserves_input_and_ignores_station_duplicates_and_labels():
    data = prepared([0.6] * 5 + [1.2], ids=["A", "B", "C", "D", "E", " F "])
    data["station_id"] = "same station"
    data["anomaly_type"] = ["injected", "injected", None, None, None, None]
    data.index = [8, 4, 8, 7, 6, 4]
    original = data.copy(deep=True)

    first = detect_statistical_anomalies(data)
    second = detect_statistical_anomalies(data[["record_id", "participation_rate"]])

    assert first["record_id"].tolist() == ["F"]
    pd.testing.assert_frame_equal(first, second)
    pd.testing.assert_frame_equal(data, original)

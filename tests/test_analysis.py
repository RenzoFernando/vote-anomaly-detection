import json
import math

import pandas as pd
import pytest

from src.analysis import summarize_data


def test_known_statistics_and_strict_json_without_mutating_input():
    data = pd.DataFrame({"participation_rate": [0, 0.5, 1, 1.5]})
    data["anomaly_type"] = [None, "injected", "injected", None]
    original = data.copy(deep=True)

    result = summarize_data(data)

    assert result == {
        "record_count": 4,
        "finite_participation_count": 4,
        "missing_participation_count": 0,
        "nonfinite_participation_count": 0,
        "invalid_participation_count": 0,
        "over_100_percent_count": 1,
        "participation_rate": pytest.approx(
            {
                "mean": 0.75, "median": 0.75, "min": 0, "max": 1.5,
                "q1": 0.375, "q3": 1.125, "std": math.sqrt(5 / 12),
            }
        ),
    }
    assert result == summarize_data(data[["participation_rate"]])
    assert result == json.loads(json.dumps(result, allow_nan=False))
    pd.testing.assert_frame_equal(data, original)


def test_rate_counts_distinguish_missing_infinite_and_invalid_values():
    data = pd.DataFrame(
        {"participation_rate": ["0.5", -0.5, 1.25, None, math.nan, math.inf, "-inf", "bad", "NaN"]}
    )

    result = summarize_data(data)

    assert result["record_count"] == 9
    assert result["finite_participation_count"] == 3
    assert result["missing_participation_count"] == 2
    assert result["nonfinite_participation_count"] == 2
    assert result["invalid_participation_count"] == 2
    assert result["over_100_percent_count"] == 1
    assert result["participation_rate"]["min"] == -0.5


@pytest.mark.parametrize("rates", [[], [None, "invalid", math.inf]])
def test_empty_or_unusable_rates_have_undefined_statistics(rates):
    result = summarize_data(pd.DataFrame({"participation_rate": rates}))

    assert result["record_count"] == len(rates)
    assert result["finite_participation_count"] == 0
    assert result["over_100_percent_count"] is None
    assert result["participation_rate"] == dict.fromkeys(["mean", "median", "min", "max", "q1", "q3", "std"])
    assert result == json.loads(json.dumps(result, allow_nan=False))


def test_single_finite_rate_has_no_sample_standard_deviation():
    data = pd.DataFrame({"participation_rate": pd.Series([pd.NA, 0.75], dtype="Float64")})

    result = summarize_data(data)

    assert result["over_100_percent_count"] == 0
    assert result["participation_rate"] == {
        "mean": 0.75, "median": 0.75, "min": 0.75, "max": 0.75, "q1": 0.75, "q3": 0.75, "std": None,
    }


@pytest.mark.parametrize("columns", [["record_id"], ["participation_rate", "participation_rate"]])
def test_rejects_missing_or_duplicate_participation_column(columns):
    with pytest.raises(ValueError, match="participation_rate"):
        summarize_data(pd.DataFrame(columns=columns))


def test_rejects_non_dataframe():
    with pytest.raises(TypeError, match="DataFrame"):
        summarize_data([0.5, 0.6])

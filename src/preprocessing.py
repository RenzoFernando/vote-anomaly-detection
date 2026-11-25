"""Preprocessing and rule-based quality checks for simulated election data."""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "electoral_dataset.csv"


REQUIRED_COLUMNS = (
    "record_id",
    "station_id",
    "registered_voters",
    "votes_candidate_a",
    "votes_candidate_b",
    "votes_candidate_c",
    "blank_votes",
    "null_votes",
    "total_votes",
)

COUNT_COLUMNS = (
    "registered_voters",
    "votes_candidate_a",
    "votes_candidate_b",
    "votes_candidate_c",
    "blank_votes",
    "null_votes",
    "total_votes",
)

BALLOT_COLUMNS = (
    "votes_candidate_a",
    "votes_candidate_b",
    "votes_candidate_c",
    "blank_votes",
    "null_votes",
)


def preprocess_dataset(dataset: pd.DataFrame) -> pd.DataFrame:
    """Normalize identifiers and numeric columns without dropping any records."""
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(dataset.columns))
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {missing_columns}")

    processed = dataset.loc[:, list(REQUIRED_COLUMNS)].copy()
    for column in ("record_id", "station_id"):
        processed[column] = processed[column].astype("string").str.strip()
    for column in COUNT_COLUMNS:
        processed[column] = pd.to_numeric(processed[column], errors="raise")
    return processed


def validate_dataset(dataset: pd.DataFrame) -> pd.DataFrame:
    """Return row-level validation issues; the input rows are never discarded."""
    processed = preprocess_dataset(dataset)
    issues: list[dict[str, str]] = []

    def add_issues(mask: pd.Series, issue_type: str, message: str) -> None:
        for record_id in processed.loc[mask, "record_id"]:
            issues.append(
                {
                    "record_id": str(record_id),
                    "issue_type": issue_type,
                    "message": message,
                }
            )

    for column in REQUIRED_COLUMNS:
        add_issues(
            processed[column].isna(),
            "missing_value",
            f"{column} is missing.",
        )

    for column in ("record_id", "station_id"):
        add_issues(
            processed[column].eq(""),
            "empty_identifier",
            f"{column} is empty.",
        )

    add_issues(
        processed["record_id"].duplicated(keep=False),
        "duplicate_record_id",
        "record_id must be unique.",
    )
    add_issues(
        processed["station_id"].duplicated(keep=False)
        & processed["station_id"].notna()
        & processed["station_id"].ne(""),
        "duplicate_station_id",
        "station_id appears more than once.",
    )

    for column in COUNT_COLUMNS:
        add_issues(
            processed[column].lt(0),
            "negative_count",
            f"{column} cannot be negative.",
        )

    ballot_sum = processed.loc[:, list(BALLOT_COLUMNS)].sum(
        axis=1, min_count=len(BALLOT_COLUMNS)
    )
    add_issues(
        ballot_sum.notna()
        & processed["total_votes"].notna()
        & ballot_sum.ne(processed["total_votes"]),
        "vote_total_mismatch",
        "total_votes must equal the sum of all ballot categories.",
    )
    add_issues(
        processed["total_votes"].notna()
        & processed["registered_voters"].notna()
        & processed["total_votes"].gt(processed["registered_voters"]),
        "turnout_over_capacity",
        "total_votes cannot exceed registered_voters.",
    )

    return pd.DataFrame(issues, columns=("record_id", "issue_type", "message"))


if __name__ == "__main__":
    generated_dataset = pd.read_csv(DATASET_PATH)
    findings = validate_dataset(generated_dataset)
    print(f"Validated {len(generated_dataset)} records from {DATASET_PATH}")
    if findings.empty:
        print("No validation issues found.")
    else:
        print(f"Found {len(findings)} validation findings:")
        print(findings.to_string(index=False))

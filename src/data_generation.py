"""Generate a reproducible synthetic election dataset for the project."""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_RECORDS = 500
DEFAULT_ANOMALIES = 25
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "electoral_dataset.csv"
GROUND_TRUTH_PATH = PROJECT_ROOT / "data" / "ground_truth" / "anomaly_labels.csv"
BALLOT_COLUMNS = (
    "votes_candidate_a",
    "votes_candidate_b",
    "votes_candidate_c",
    "blank_votes",
    "null_votes",
)


def generate_dataset(
    n_records: int = DEFAULT_RECORDS,
    n_anomalies: int | None = None,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return simulated polling-station results and separate anomaly labels."""
    if n_records < 4:
        raise ValueError("n_records must be at least 4 to inject all anomaly types.")
    if n_anomalies is None:
        n_anomalies = max(4, round(n_records * DEFAULT_ANOMALIES / DEFAULT_RECORDS))
    if n_anomalies < 4:
        raise ValueError("n_anomalies must be at least 4 to include all anomaly types.")
    if n_anomalies > n_records:
        raise ValueError("n_anomalies cannot exceed n_records.")

    rng = np.random.default_rng(seed)
    registered_voters = rng.integers(250, 801, size=n_records)
    turnout_rates = rng.uniform(0.55, 0.90, size=n_records)
    total_votes = np.floor(registered_voters * turnout_rates).astype(int)
    vote_shares = rng.dirichlet([7, 5, 3, 0.7, 0.5], size=n_records)
    vote_counts = np.array(
        [
            rng.multinomial(int(total), shares)
            for total, shares in zip(total_votes, vote_shares)
        ]
    )

    dataset = pd.DataFrame(
        {
            "record_id": [f"REC-{index:04d}" for index in range(1, n_records + 1)],
            "station_id": [
                f"ST-{index:04d}" for index in range(1, n_records + 1)
            ],
            "registered_voters": registered_voters,
            "votes_candidate_a": vote_counts[:, 0],
            "votes_candidate_b": vote_counts[:, 1],
            "votes_candidate_c": vote_counts[:, 2],
            "blank_votes": vote_counts[:, 3],
            "null_votes": vote_counts[:, 4],
            "total_votes": total_votes,
        }
    )

    anomaly_types = [
        "turnout_over_capacity",
        "negative_vote_count",
        "vote_total_mismatch",
        "duplicate_station_id",
    ]
    selected_rows = rng.choice(n_records, size=n_anomalies, replace=False)
    selected_types = anomaly_types + list(
        rng.choice(anomaly_types, size=n_anomalies - len(anomaly_types))
    )
    rng.shuffle(selected_types)
    injected_anomalies = list(zip(selected_rows, selected_types))
    duplicate_rows = {
        row_index
        for row_index, anomaly_type in injected_anomalies
        if anomaly_type == "duplicate_station_id"
    }
    base_station_row = next(
        row_index for row_index in range(n_records) if row_index not in duplicate_rows
    )

    for row_index, anomaly_type in injected_anomalies:
        if anomaly_type == "turnout_over_capacity":
            dataset.at[row_index, "votes_candidate_a"] += (
                dataset.at[row_index, "registered_voters"]
                + 1
                - dataset.at[row_index, "total_votes"]
            )
            dataset.at[row_index, "total_votes"] = (
                dataset.at[row_index, "registered_voters"] + 1
            )
        elif anomaly_type == "negative_vote_count":
            dataset.at[row_index, "votes_candidate_c"] = -2
            dataset.at[row_index, "total_votes"] = dataset.loc[
                row_index, list(BALLOT_COLUMNS)
            ].sum()
        elif anomaly_type == "vote_total_mismatch":
            dataset.at[row_index, "total_votes"] += 7
        elif anomaly_type == "duplicate_station_id":
            dataset.at[row_index, "station_id"] = dataset.at[
                base_station_row, "station_id"
            ]

    labels = pd.DataFrame(
        [
            {"record_id": dataset.at[index, "record_id"], "anomaly_type": kind}
            for index, kind in injected_anomalies
        ]
    )
    return dataset, labels


def save_dataset(
    dataset: pd.DataFrame,
    labels: pd.DataFrame,
    dataset_path: Path = RAW_DATA_PATH,
    labels_path: Path = GROUND_TRUTH_PATH,
) -> None:
    """Save generated data and its reference labels in separate CSV files."""
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(dataset_path, index=False)
    labels.to_csv(labels_path, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--records",
        type=int,
        default=DEFAULT_RECORDS,
        help=f"number of simulated records (default: {DEFAULT_RECORDS})",
    )
    parser.add_argument(
        "--anomalies",
        type=int,
        default=None,
        help="number of anomalous records (default: 5%% of records, minimum 4)",
    )
    parser.add_argument("--seed", type=int, default=42, help="random seed (default: 42)")
    args = parser.parse_args()

    generated_dataset, anomaly_labels = generate_dataset(
        n_records=args.records,
        n_anomalies=args.anomalies,
        seed=args.seed,
    )
    save_dataset(generated_dataset, anomaly_labels)
    print(f"Generated {len(generated_dataset)} records at {RAW_DATA_PATH}")
    print("\nDataset preview:")
    print(generated_dataset.head().to_string(index=False))
    print(f"\nRecorded anomaly labels at {GROUND_TRUTH_PATH}:")
    print(anomaly_labels.to_string(index=False))

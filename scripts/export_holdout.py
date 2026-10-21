"""Export train.py's held-out test split, so the quality gate runs without the full dataset."""

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from pm_service.preprocessing import COLUMN_RENAME, TARGET, load_dataset
from train import RANDOM_STATE, TEST_SIZE

RAW_COLUMNS: list[str] = list(COLUMN_RENAME)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/raw/ai4i2020.csv"))
    parser.add_argument("--output", type=Path, default=Path("tests/data/holdout.csv"))
    args = parser.parse_args()

    # Same split call and parameters as train.py, so the rows are exactly its test set.
    df = load_dataset(args.data)
    _, test_df = train_test_split(
        df, test_size=TEST_SIZE, stratify=df[TARGET], random_state=RANDOM_STATE
    )
    raw = pd.read_csv(args.data).loc[test_df.index, RAW_COLUMNS]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.output, index=False)
    print(f"Saved {len(raw)} rows ({int(raw['Machine failure'].sum())} failures) to {args.output}")


if __name__ == "__main__":
    main()

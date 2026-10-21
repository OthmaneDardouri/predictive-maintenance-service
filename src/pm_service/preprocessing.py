from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

COLUMN_RENAME: dict[str, str] = {
    "Type": "type",
    "Air temperature [K]": "air_temperature_k",
    "Process temperature [K]": "process_temperature_k",
    "Rotational speed [rpm]": "rotational_speed_rpm",
    "Torque [Nm]": "torque_nm",
    "Tool wear [min]": "tool_wear_min",
    "Machine failure": "machine_failure",
}

CATEGORICAL_FEATURES: list[str] = ["type"]
NUMERIC_FEATURES: list[str] = [
    "air_temperature_k",
    "process_temperature_k",
    "rotational_speed_rpm",
    "torque_nm",
    "tool_wear_min",
]
FEATURES: list[str] = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET: str = "machine_failure"

# Failure-mode flags are set together with the target, so using them as features is leakage.
LEAKAGE_COLUMNS: list[str] = ["TWF", "HDF", "PWF", "OSF", "RNF"]
ID_COLUMNS: list[str] = ["UDI", "Product ID"]


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = set(COLUMN_RENAME) - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing columns: {sorted(missing)}")
    return df.rename(columns=COLUMN_RENAME)


def split_features_target(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    return df[FEATURES].copy(), df[TARGET].copy()


def build_preprocessor() -> ColumnTransformer:
    # Numeric features pass through unscaled: tree models don't need scaling.
    return ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("numeric", "passthrough", NUMERIC_FEATURES),
        ]
    )

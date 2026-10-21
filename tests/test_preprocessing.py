from pathlib import Path

import pandas as pd
import pytest

from pm_service.preprocessing import (
    FEATURES,
    ID_COLUMNS,
    LEAKAGE_COLUMNS,
    TARGET,
    build_preprocessor,
    load_dataset,
    split_features_target,
)

RAW_ROWS: list[dict[str, object]] = [
    {
        "UDI": 1, "Product ID": "M14860", "Type": "M",
        "Air temperature [K]": 298.1, "Process temperature [K]": 308.6,
        "Rotational speed [rpm]": 1551, "Torque [Nm]": 42.8, "Tool wear [min]": 0,
        "Machine failure": 0, "TWF": 0, "HDF": 0, "PWF": 0, "OSF": 0, "RNF": 0,
    },
    {
        "UDI": 2, "Product ID": "L47181", "Type": "L",
        "Air temperature [K]": 298.2, "Process temperature [K]": 308.7,
        "Rotational speed [rpm]": 1408, "Torque [Nm]": 46.3, "Tool wear [min]": 3,
        "Machine failure": 1, "TWF": 0, "HDF": 1, "PWF": 0, "OSF": 0, "RNF": 0,
    },
    {
        "UDI": 3, "Product ID": "H29424", "Type": "H",
        "Air temperature [K]": 298.3, "Process temperature [K]": 308.5,
        "Rotational speed [rpm]": 1498, "Torque [Nm]": 49.4, "Tool wear [min]": 5,
        "Machine failure": 0, "TWF": 0, "HDF": 0, "PWF": 0, "OSF": 0, "RNF": 0,
    },
]


@pytest.fixture
def raw_csv(tmp_path: Path) -> Path:
    path = tmp_path / "sample.csv"
    pd.DataFrame(RAW_ROWS).to_csv(path, index=False)
    return path


def test_load_dataset_renames_columns(raw_csv: Path) -> None:
    df = load_dataset(raw_csv)

    assert set(FEATURES) <= set(df.columns)
    assert TARGET in df.columns


def test_load_dataset_fails_on_missing_column(tmp_path: Path) -> None:
    path = tmp_path / "broken.csv"
    pd.DataFrame(RAW_ROWS).drop(columns=["Torque [Nm]"]).to_csv(path, index=False)

    with pytest.raises(ValueError, match="Torque"):
        load_dataset(path)


def test_split_excludes_leakage_and_id_columns(raw_csv: Path) -> None:
    X, y = split_features_target(load_dataset(raw_csv))

    assert list(X.columns) == FEATURES
    for column in LEAKAGE_COLUMNS + ID_COLUMNS + [TARGET]:
        assert column not in X.columns
    assert y.tolist() == [0, 1, 0]


def test_preprocessor_output_shape(raw_csv: Path) -> None:
    X, _ = split_features_target(load_dataset(raw_csv))

    transformed = build_preprocessor().fit_transform(X)

    # 3 one-hot columns for Type (L, M, H) + 5 numeric columns.
    assert transformed.shape == (3, 8)


def test_preprocessor_ignores_unknown_type(raw_csv: Path) -> None:
    X, _ = split_features_target(load_dataset(raw_csv))
    preprocessor = build_preprocessor().fit(X)
    unseen = X.head(1).assign(type="Z")

    transformed = preprocessor.transform(unseen)

    assert transformed[0, :3].tolist() == [0.0, 0.0, 0.0]

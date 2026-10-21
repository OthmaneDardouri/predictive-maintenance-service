from pathlib import Path
from typing import Any

import pytest
from sklearn.metrics import average_precision_score, recall_score

from pm_service.model import LoadedModel, load_model
from pm_service.preprocessing import load_dataset, split_features_target

ROOT = Path(__file__).resolve().parents[1]
HOLDOUT_PATH = ROOT / "tests" / "data" / "holdout.csv"

# v0.1.0 scores recall 0.66 (45/68 failures) and PR-AUC 0.76 on the holdout.
# Each missed failure costs ~1.5 recall points: 0.60 tolerates ~4 extra misses from
# retraining noise, but blocks a model that clearly finds fewer failures.
MIN_RECALL = 0.60
MIN_PR_AUC = 0.70


@pytest.fixture(scope="module")
def model() -> LoadedModel:
    return load_model(ROOT / "models" / "model.joblib")


@pytest.fixture(scope="module")
def holdout_scores(model: LoadedModel) -> dict[str, Any]:
    X, y = split_features_target(load_dataset(HOLDOUT_PATH))
    probabilities = model.pipeline.predict_proba(X)[:, 1]
    predictions = (probabilities >= model.threshold).astype(int)
    return {
        "recall": recall_score(y, predictions),
        "pr_auc": average_precision_score(y, probabilities),
    }


def test_recall_on_failures_above_gate(holdout_scores: dict[str, Any]) -> None:
    assert holdout_scores["recall"] >= MIN_RECALL


def test_pr_auc_above_gate(holdout_scores: dict[str, Any]) -> None:
    assert holdout_scores["pr_auc"] >= MIN_PR_AUC


def test_holdout_matches_training_metrics(
    model: LoadedModel, holdout_scores: dict[str, Any]
) -> None:
    # Proves the holdout is the real test split and the committed model matches its metadata.
    assert holdout_scores["recall"] == pytest.approx(model.metadata["metrics"]["recall"])
    assert holdout_scores["pr_auc"] == pytest.approx(model.metadata["metrics"]["pr_auc"])

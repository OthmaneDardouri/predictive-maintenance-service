import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import joblib
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from pm_service.preprocessing import (
    FEATURES,
    TARGET,
    build_preprocessor,
    load_dataset,
    split_features_target,
)

MODEL_VERSION = "0.1.0"
RANDOM_STATE = 42
TEST_SIZE = 0.2
DECISION_THRESHOLD = 0.5

logger = logging.getLogger("train")


def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=200,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the machine failure model.")
    parser.add_argument("--data", type=Path, default=Path("data/raw/ai4i2020.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("models"))
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()

    X, y = split_features_target(load_dataset(args.data))
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    logger.info(
        "Split: train=%d (failure rate %.4f), test=%d (failure rate %.4f)",
        len(X_train), y_train.mean(), len(X_test), y_test.mean(),
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    probabilities = pipeline.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= DECISION_THRESHOLD).astype(int)
    metrics = {
        "precision": float(precision_score(y_test, predictions)),
        "recall": float(recall_score(y_test, predictions)),
        "f1": float(f1_score(y_test, predictions)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        # PR-AUC of a random classifier equals the positive rate.
        "pr_auc_baseline": float(y_test.mean()),
    }
    tn, fp, fn, tp = confusion_matrix(y_test, predictions).ravel()
    logger.info("Metrics on failure class: %s", json.dumps(metrics, indent=2))
    logger.info("Confusion matrix: TN=%d FP=%d FN=%d TP=%d", tn, fp, fn, tp)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "model.joblib"
    joblib.dump(pipeline, model_path)

    metadata = {
        "model_version": MODEL_VERSION,
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(UTC).isoformat(),
        "features": FEATURES,
        "target": TARGET,
        "decision_threshold": DECISION_THRESHOLD,
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "metrics": metrics,
    }
    (args.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    logger.info("Saved model to %s", model_path)


if __name__ == "__main__":
    main()

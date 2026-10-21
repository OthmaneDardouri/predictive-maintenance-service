import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from pm_service.preprocessing import FEATURES


@dataclass(frozen=True)
class LoadedModel:
    pipeline: Pipeline
    metadata: dict[str, Any]

    @property
    def version(self) -> str:
        return str(self.metadata["model_version"])

    @property
    def threshold(self) -> float:
        return float(self.metadata["decision_threshold"])

    def predict_failure_probability(self, features: dict[str, Any]) -> float:
        row = pd.DataFrame([features], columns=FEATURES)
        return float(self.pipeline.predict_proba(row)[0, 1])


def load_model(model_path: Path) -> LoadedModel:
    pipeline = joblib.load(model_path)
    metadata = json.loads((model_path.parent / "metadata.json").read_text())
    return LoadedModel(pipeline=pipeline, metadata=metadata)

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
from sklearn.pipeline import Pipeline


@dataclass(frozen=True)
class LoadedModel:
    pipeline: Pipeline
    metadata: dict[str, Any]

    @property
    def version(self) -> str:
        return str(self.metadata["model_version"])


def load_model(model_path: Path) -> LoadedModel:
    pipeline = joblib.load(model_path)
    metadata = json.loads((model_path.parent / "metadata.json").read_text())
    return LoadedModel(pipeline=pipeline, metadata=metadata)

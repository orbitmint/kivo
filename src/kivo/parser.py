import os
from typing import List
import yaml
from kivo.models.model import Model

def load_model_from_yaml(file_path: str) -> Model:
    """Loads and validates a Kivo Model from a YAML file."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Model.model_validate(data)

def load_models_from_directory(dir_path: str) -> List[Model]:
    """Loads and validates all Kivo Models from a directory of YAML files."""
    models = []
    if not os.path.exists(dir_path):
        return models
    for entry in os.scandir(dir_path):
        if entry.is_file() and entry.name.endswith((".yaml", ".yml")):
            try:
                model = load_model_from_yaml(entry.path)
                models.append(model)
            except Exception as e:
                # Re-raise with filename context for easier troubleshooting
                raise RuntimeError(f"Error parsing model file {entry.name}: {e}") from e
    return models

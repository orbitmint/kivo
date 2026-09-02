import os
from typing import List, Dict, Any
import yaml
from kivo.models.model import Model
from kivo.models.dimension import Dimension
from kivo.models.metric import Metric

def parse_ossie_to_kivo_models(data: Dict[str, Any]) -> List[Model]:
    """Parses Apache Ossie semantic model specification into Kivo Models."""
    kivo_models = []
    
    semantic_models = data.get("semantic_model", [])
    for model in semantic_models:
        model_name = model.get("name", "unknown_model")
        model_desc = model.get("description", "")
        
        # 1. Parse datasets to extract table source and dimensions
        datasets = model.get("datasets", [])
        source_table = ""
        source_sql = ""
        dimensions = []

        if datasets:
            # Use source from the first dataset as table/sql
            source = datasets[0].get("source", "")
            if source.strip().upper().startswith("SELECT"):
                source_sql = source
            else:
                source_table = source
            
            # Extract fields designated as dimensions
            for dataset in datasets:
                for field in dataset.get("fields", []):
                    field_name = field.get("name")
                    is_dim = "dimension" in field or field.get("dimension") is not None
                    
                    if is_dim:
                        dim_info = field.get("dimension")
                        is_time = False
                        if isinstance(dim_info, dict):
                            is_time = dim_info.get("is_time", False)
                        
                        dimensions.append(Dimension(
                            name=field_name,
                            type="time" if is_time else "categorical",
                            sql_expr=field_name
                        ))

        # 2. Parse metrics
        metrics = model.get("metrics", [])
        for metric in metrics:
            metric_name = metric.get("name")
            
            # Attempt to extract aggregation and expression
            agg_type = "sum"
            expr_str = ""
            expression_block = metric.get("expression", {})
            if isinstance(expression_block, dict):
                dialects = expression_block.get("dialects", [])
                if dialects and isinstance(dialects, list):
                    expr_str = dialects[0].get("expression", "").upper()
                elif "expression" in expression_block:
                    expr_str = str(expression_block.get("expression", "")).upper()

            if "SUM(" in expr_str:
                agg_type = "sum"
            elif "COUNT(" in expr_str:
                agg_type = "count"
            elif "AVG(" in expr_str:
                agg_type = "avg"
            elif "MIN(" in expr_str:
                agg_type = "min"
            elif "MAX(" in expr_str:
                agg_type = "max"

            # Create a dedicated Kivo model for each metric
            # because Kivo's base compiler operates at the Model level
            kivo_metrics = [Metric(
                name=metric_name,
                type=agg_type,
                sql_expr=metric_name
            )]

            kivo_model_data = {
                "name": metric_name,
                "dimensions": dimensions,
                "metrics": kivo_metrics
            }
            if source_sql:
                kivo_model_data["sql"] = source_sql
            else:
                kivo_model_data["table"] = source_table

            kivo_models.append(Model(**kivo_model_data))

    return kivo_models

def load_model_from_yaml(file_path: str) -> Model:
    """Loads and validates a Kivo Model from a YAML file (supports native and Apache Ossie formats)."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    if not data or not isinstance(data, dict):
        raise ValueError(f"Invalid or empty YAML file: {file_path}")

    # Check if this is Apache Ossie format
    if "semantic_model" in data:
        models = parse_ossie_to_kivo_models(data)
        if not models:
            raise ValueError(f"No semantic models found in Ossie spec: {file_path}")
        return models[0]  # Return the first model when querying singular file
        
    return Model.model_validate(data)

def load_models_from_directory(dir_path: str) -> List[Model]:
    """Loads and validates all Kivo Models from a directory of YAML files (supports both native and Ossie)."""
    models = []
    if not os.path.exists(dir_path):
        return models
    for entry in os.scandir(dir_path):
        if entry.is_file() and entry.name.endswith((".yaml", ".yml")):
            try:
                with open(entry.path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                
                if not data or not isinstance(data, dict):
                    continue

                if "semantic_model" in data:
                    ossie_models = parse_ossie_to_kivo_models(data)
                    models.extend(ossie_models)
                else:
                    models.append(Model.model_validate(data))
            except Exception as e:
                raise RuntimeError(f"Error parsing model file {entry.name}: {e}") from e
    return models

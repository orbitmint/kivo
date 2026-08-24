from typing import Dict, List, Optional
import pyarrow as pa
from kivo.models.model import Model
from kivo.parser import load_model_from_yaml, load_models_from_directory
from kivo.compiler.sql_builder import SQLCompiler
from kivo.executors.base import BaseExecutor

class KivoEngine:
    def __init__(self, default_dialect: Optional[str] = None):
        """
        Initializes the KivoEngine.
        
        :param default_dialect: The default SQLGlot dialect to use when compiling.
        """
        self.models: Dict[str, Model] = {}
        self.compiler = SQLCompiler(dialect=default_dialect)

    def load_model(self, file_path: str) -> Model:
        """Loads and caches a single model from a YAML file."""
        model = load_model_from_yaml(file_path)
        self.models[model.name] = model
        return model

    def load_models(self, dir_path: str) -> List[Model]:
        """Loads and caches all models from a directory of YAML files."""
        models = load_models_from_directory(dir_path)
        for m in models:
            self.models[m.name] = m
        return models

    def get_model(self, model_name: str) -> Model:
        """Retrieves a loaded model by name."""
        if model_name not in self.models:
            raise ValueError(f"Model '{model_name}' is not loaded in KivoEngine.")
        return self.models[model_name]

    def compile(
        self,
        model_name: str,
        dimensions: List[str],
        metrics: List[str],
        filters: Optional[List[str]] = None,
        dialect: Optional[str] = None
    ) -> str:
        """
        Compiles a semantic query request for a model into SQL.
        
        :param model_name: The name of the loaded model to query.
        :param dimensions: Dimension names to select and group by.
        :param metrics: Metric names to compute.
        :param filters: Optional list of query-level filter expressions.
        :param dialect: Optional SQL dialect override.
        :return: Compiled SQL string.
        """
        model = self.get_model(model_name)
        return self.compiler.compile(
            model=model,
            dimensions=dimensions,
            metrics=metrics,
            filters=filters,
            dialect=dialect
        )

    def query(
        self,
        model_name: str,
        dimensions: List[str],
        metrics: List[str],
        executor: BaseExecutor,
        filters: Optional[List[str]] = None,
        dialect: Optional[str] = None
    ) -> pa.Table:
        """
        Compiles and executes a semantic query, returning results as a PyArrow Table.
        
        :param model_name: The name of the loaded model to query.
        :param dimensions: Dimension names to select and group by.
        :param metrics: Metric names to compute.
        :param executor: An instance of BaseExecutor to run the query.
        :param filters: Optional list of query-level filter expressions.
        :param dialect: Optional SQL dialect override (auto-detected if None).
        :return: A pyarrow.Table containing the query results.
        """
        if dialect is None:
            # Smart dialect inference from executor type
            from kivo.executors.duckdb_exec import DuckDBExecutor
            from kivo.executors.postgres_exec import PostgreSQLExecutor
            from kivo.executors.clickhouse_exec import ClickHouseExecutor
            from kivo.executors.bigquery_exec import BigQueryExecutor

            if isinstance(executor, DuckDBExecutor):
                dialect = "duckdb"
            elif isinstance(executor, PostgreSQLExecutor):
                dialect = "postgres"
            elif isinstance(executor, ClickHouseExecutor):
                dialect = "clickhouse"
            elif isinstance(executor, BigQueryExecutor):
                dialect = "bigquery"
            else:
                dialect = None

        sql = self.compile(
            model_name=model_name,
            dimensions=dimensions,
            metrics=metrics,
            filters=filters,
            dialect=dialect
        )
        return executor.execute_query(sql)

    def export_llm_schema(self, model_name: str) -> str:
        """
        Generates an LLM-optimized Markdown schema prompt for a loaded model.
        This prompt instructs an LLM on how to formulate semantic query requests
        instead of writing raw SQL queries.
        """
        model = self.get_model(model_name)
        
        dimensions_list = []
        for d in model.dimensions:
            dimensions_list.append(f"- **{d.name}** ({d.type}): `{d.sql_expr}`")
            
        metrics_list = []
        for m in model.metrics:
            metrics_list.append(f"- **{m.name}** ({m.type}): `{m.sql_expr}`")
            
        prompt = f"""# SYSTEM INSTRUCTIONS: AI Semantic Query Translator

You are an expert AI Data Analyst. Your sole job is to translate natural language questions from users into a structured JSON query request for the **Kivo Semantic Layer**.

### Your Constraints:
1. **DO NOT WRITE RAW SQL.** You do not have direct access to database tables or physical columns.
2. **Strict Output Format:** You must respond ONLY with a valid JSON block containing the query request. Do not add conversational filler, preambles, or markdown outside the JSON block.

---

## 1. Available Semantic Schema for Model: '{model.name}'

### Available Dimensions (Grouping & Filtering):
{chr(10).join(dimensions_list)}

### Available Metrics (Calculations & Measures):
{chr(10).join(metrics_list)}

---

## 2. Query Request JSON Schema

Your output must be a JSON object adhering to this schema:
```json
{{
  "model_name": "{model.name}",
  "dimensions": ["dimension_name_1", "dimension_name_2"],
  "metrics": ["metric_name_1", "metric_name_2"],
  "filters": ["filter_expression_1", "filter_expression_2"]
}}
```

### Filtering Guidelines:
- Only filter using the semantic names of dimensions (e.g., `country = 'US'` or `date >= '2026-01-01'`).
- Combine filters into a list of strings. Each string represents an independent SQL condition (do not join them with AND/OR within the same string; Kivo will automatically combine them with AND).
- Do not use database-specific dialects for expressions. Use simple standard ANSI SQL operators (`=`, `>`, `<`, `>=`, `<=`, `LIKE`, `IN`).

---

## 3. Reference Examples

### Example 1: Simple Aggregation
**User Question:** "What is our total revenue and order count by country?"
**Your JSON Output:**
```json
{{
  "model_name": "{model.name}",
  "dimensions": ["country"],
  "metrics": ["total_revenue", "total_orders"]
}}
```

### Example 2: Metric-Level & Query-Level Filters
**User Question:** "Show average order value by date for US completed orders."
**Your JSON Output:**
```json
{{
  "model_name": "{model.name}",
  "dimensions": ["date"],
  "metrics": ["average_order_value"],
  "filters": ["country = 'US'", "status = 'completed'"]
}}
```
"""
        return prompt

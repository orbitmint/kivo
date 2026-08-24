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

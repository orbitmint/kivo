import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from kivo.engine import KivoEngine
from kivo.executors import (
    BaseExecutor,
    DuckDBExecutor,
    PostgreSQLExecutor,
    ClickHouseExecutor,
    BigQueryExecutor
)

# Initialize FastAPI App
app = FastAPI(
    title="Kivo Semantic API Server",
    description="Exposes the open-source Kivo semantic layer over HTTP.",
    version="0.1.0"
)

# Global Engine Instance
engine = KivoEngine()

# Automatically load models on startup if KIVO_MODELS_DIR is defined
MODELS_DIR = os.getenv("KIVO_MODELS_DIR", "models")
if os.path.exists(MODELS_DIR):
    try:
        loaded = engine.load_models(MODELS_DIR)
        print(f"Loaded {len(loaded)} semantic models from '{MODELS_DIR}' directory.")
    except Exception as e:
        print(f"Error loading models from '{MODELS_DIR}': {e}")
elif os.path.exists("tests/data/"):
    # Fallback to tests/data for easy out-of-the-box local developer onboarding
    try:
        loaded = engine.load_models("tests/data")
        print(f"Loaded {len(loaded)} semantic models from 'tests/data' default directory.")
    except Exception as e:
        pass


def get_executor() -> BaseExecutor:
    """Instantiates and returns the configured database executor based on environment variables."""
    db_type = os.getenv("KIVO_DATABASE_TYPE", "duckdb").lower()
    
    try:
        if db_type == "duckdb":
            db_path = os.getenv("KIVO_DUCKDB_PATH", ":memory:")
            return DuckDBExecutor(db_path=db_path)
            
        elif db_type == "postgres":
            host = os.getenv("KIVO_PG_HOST", "localhost")
            port = int(os.getenv("KIVO_PG_PORT", "5432"))
            dbname = os.getenv("KIVO_PG_DB", "postgres")
            user = os.getenv("KIVO_PG_USER", "postgres")
            password = os.getenv("KIVO_PG_PASSWORD", "")
            return PostgreSQLExecutor(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password
            )
            
        elif db_type == "clickhouse":
            host = os.getenv("KIVO_CLICKHOUSE_HOST", "localhost")
            port = int(os.getenv("KIVO_CLICKHOUSE_PORT", "8123"))
            user = os.getenv("KIVO_CLICKHOUSE_USER", "default")
            password = os.getenv("KIVO_CLICKHOUSE_PASSWORD", "")
            database = os.getenv("KIVO_CLICKHOUSE_DB", "default")
            return ClickHouseExecutor(
                host=host,
                port=port,
                username=user,
                password=password,
                database=database
            )
            
        elif db_type == "bigquery":
            project = os.getenv("KIVO_BIGQUERY_PROJECT")
            location = os.getenv("KIVO_BIGQUERY_LOCATION")
            client_kwargs = {}
            if project:
                client_kwargs["project"] = project
            if location:
                client_kwargs["location"] = location
            return BigQueryExecutor(**client_kwargs)
            
        else:
            raise ValueError(f"Unsupported database type '{db_type}'")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to database executor of type '{db_type}': {e}"
        )


# API Models
class CompileRequest(BaseModel):
    model_name: str = Field(description="Name of the semantic model to query.")
    dimensions: List[str] = Field(default_factory=list, description="List of dimensions to group/select by.")
    metrics: List[str] = Field(default_factory=list, description="List of metrics to compute.")
    filters: Optional[List[str]] = Field(default=None, description="Query-level where filter expressions.")
    dialect: Optional[str] = Field(default=None, description="Override SQL compile dialect.")

class QueryRequest(BaseModel):
    model_name: str = Field(description="Name of the semantic model to query.")
    dimensions: List[str] = Field(default_factory=list, description="List of dimensions to group/select by.")
    metrics: List[str] = Field(default_factory=list, description="List of metrics to compute.")
    filters: Optional[List[str]] = Field(default=None, description="Query-level where filter expressions.")


@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Kivo Semantic API Server",
        "status": "healthy",
        "loaded_models": list(engine.models.keys())
    }


@app.get("/models")
def list_models():
    """Discovers and lists all loaded semantic models with their dimensions and metrics."""
    result = []
    for model_name, model in engine.models.items():
        result.append({
            "name": model_name,
            "table": model.table,
            "sql": model.sql,
            "dimensions": [
                {"name": d.name, "type": d.type, "expr": d.sql_expr}
                for d in model.dimensions
            ],
            "metrics": [
                {"name": m.name, "type": m.type, "expr": m.sql_expr, "filters": m.filters}
                for m in model.metrics
            ]
        })
    return {"models": result}


@app.post("/compile")
def compile_query(request: CompileRequest):
    """Compiles a semantic query request into raw SQL without executing it."""
    try:
        sql = engine.compile(
            model_name=request.model_name,
            dimensions=request.dimensions,
            metrics=request.metrics,
            filters=request.filters,
            dialect=request.dialect
        )
        return {"sql": sql}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compilation error: {e}")


@app.post("/query")
def execute_query(request: QueryRequest, executor: BaseExecutor = Depends(get_executor)):
    """Compiles and executes a semantic query, returning results as a structured JSON object."""
    try:
        # We run the query using the configured executor
        with executor:
            result_table = engine.query(
                model_name=request.model_name,
                dimensions=request.dimensions,
                metrics=request.metrics,
                filters=request.filters,
                executor=executor
            )
            # Convert PyArrow Table to dictionary of lists for JSON response
            return {
                "rows_count": result_table.num_rows,
                "data": result_table.to_pydict()
            }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error: {e}")

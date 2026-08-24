import pytest
from fastapi.testclient import TestClient
import pyarrow as pa
import duckdb
from kivo.server import app, get_executor
from kivo.executors.duckdb_exec import DuckDBExecutor

@pytest.fixture
def test_db_conn():
    # Setup standard integration dataset in an in-memory DuckDB
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE raw_sales (
            transaction_date VARCHAR,
            customer_country VARCHAR,
            order_id INTEGER,
            amount DOUBLE,
            status VARCHAR
        )
    """)
    conn.execute("""
        INSERT INTO raw_sales VALUES
        ('2026-08-20', 'US', 1, 100.0, 'completed'),
        ('2026-08-20', 'US', 2, 50.0, 'completed'),
        ('2026-08-21', 'CA', 3, 200.0, 'completed')
    """)
    yield conn
    conn.close()

@pytest.fixture
def client(test_db_conn):
    # Override the get_executor dependency of the FastAPI app
    def override_get_executor():
        return DuckDBExecutor(connection=test_db_conn)
        
    app.dependency_overrides[get_executor] = override_get_executor
    with TestClient(app) as test_client:
        yield test_client
    # Clear overrides after test
    app.dependency_overrides.clear()

def test_healthcheck(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "sales" in data["loaded_models"]

def test_list_models(client):
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    models = {m["name"]: m for m in data["models"]}
    assert "sales" in models
    sales_model = models["sales"]
    assert len(sales_model["dimensions"]) == 2
    assert len(sales_model["metrics"]) == 5

def test_compile_endpoint(client):
    payload = {
        "model_name": "sales",
        "dimensions": ["country"],
        "metrics": ["total_revenue", "average_order_value"],
        "dialect": "duckdb"
    }
    response = client.post("/compile", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "sql" in data
    sql = data["sql"]
    assert "WITH kivo_base_metrics AS" in sql
    assert "customer_country AS country" in sql

def test_compile_endpoint_failures(client):
    # Missing model
    payload = {
        "model_name": "non_existent_model",
        "dimensions": ["country"],
        "metrics": ["total_revenue"]
    }
    response = client.post("/compile", json=payload)
    assert response.status_code == 400
    assert "is not loaded" in response.json()["detail"]

def test_query_endpoint(client):
    payload = {
        "model_name": "sales",
        "dimensions": ["country"],
        "metrics": ["total_revenue", "total_orders", "average_order_value"]
    }
    response = client.post("/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["rows_count"] == 2
    
    rows = data["data"]
    # CA validations
    ca_idx = rows["country"].index("CA")
    assert rows["total_revenue"][ca_idx] == 200.0
    assert rows["total_orders"][ca_idx] == 1
    assert rows["average_order_value"][ca_idx] == 200.0
    
    # US validations
    us_idx = rows["country"].index("US")
    assert rows["total_revenue"][us_idx] == 150.0
    assert rows["total_orders"][us_idx] == 2
    assert rows["average_order_value"][us_idx] == 75.0

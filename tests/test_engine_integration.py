import duckdb
import pyarrow as pa
import pytest
from kivo.engine import KivoEngine
from kivo.executors.duckdb_exec import DuckDBExecutor

@pytest.fixture
def db_conn():
    # Create an in-memory DuckDB connection and set up a sample dataset
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
        ('2026-08-20', 'CA', 3, 200.0, 'completed'),
        ('2026-08-21', 'US', 4, 150.0, 'pending'),
        ('2026-08-21', 'CA', 5, 80.0, 'completed')
    """)
    
    yield conn
    conn.close()

def test_engine_end_to_end(db_conn):
    # Setup KivoEngine and DuckDBExecutor
    engine = KivoEngine()
    engine.load_model("tests/data/sales_model.yaml")
    
    executor = DuckDBExecutor(connection=db_conn)
    
    # 1. Query: dimensions: [country], metrics: [total_revenue, total_orders, average_order_value, completed_revenue]
    result_table = engine.query(
        model_name="sales",
        dimensions=["country"],
        metrics=["total_revenue", "total_orders", "average_order_value", "completed_revenue"],
        executor=executor
    )
    
    # Verify we got a PyArrow Table
    assert isinstance(result_table, pa.Table)
    
    # Convert to dictionary of lists for easy verification
    data = result_table.to_pydict()
    
    # Sort indexes to align US and CA consistently
    rows = list(zip(data["country"], data["total_revenue"], data["total_orders"], data["average_order_value"], data["completed_revenue"]))
    rows_sorted = sorted(rows, key=lambda x: x[0])
    
    # Assert CA results
    assert rows_sorted[0][0] == "CA"
    assert rows_sorted[0][1] == 280.0   # total_revenue (200 + 80)
    assert rows_sorted[0][2] == 2       # total_orders
    assert rows_sorted[0][3] == 140.0   # average_order_value (280 / 2)
    assert rows_sorted[0][4] == 280.0   # completed_revenue (both are completed)
    
    # Assert US results
    assert rows_sorted[1][0] == "US"
    assert rows_sorted[1][1] == 300.0   # total_revenue (100 + 50 + 150)
    assert rows_sorted[1][2] == 3       # total_orders
    assert rows_sorted[1][3] == 100.0   # average_order_value (300 / 3)
    assert rows_sorted[1][4] == 150.0   # completed_revenue (order 4 is pending, so 100 + 50 = 150)

def test_engine_query_with_filters(db_conn):
    engine = KivoEngine()
    engine.load_model("tests/data/sales_model.yaml")
    
    executor = DuckDBExecutor(connection=db_conn)
    
    # Query: dimensions: [date], metrics: [total_revenue, average_order_value]
    # Filter where country = 'US'
    result_table = engine.query(
        model_name="sales",
        dimensions=["date"],
        metrics=["total_revenue", "average_order_value"],
        executor=executor,
        filters=["customer_country = 'US'"]
    )
    
    data = result_table.to_pydict()
    rows = list(zip(data["date"], data["total_revenue"], data["average_order_value"]))
    rows_sorted = sorted(rows, key=lambda x: x[0])
    
    # For US:
    # '2026-08-20' has order 1 (100.0) and order 2 (50.0) => sum = 150.0, count = 2, avg = 75.0
    # '2026-08-21' has order 4 (150.0) => sum = 150.0, count = 1, avg = 150.0
    
    assert len(rows_sorted) == 2
    assert rows_sorted[0][0] == "2026-08-20"
    assert rows_sorted[0][1] == 150.0
    assert rows_sorted[0][2] == 75.0
    
    assert rows_sorted[1][0] == "2026-08-21"
    assert rows_sorted[1][1] == 150.0
    assert rows_sorted[1][2] == 150.0

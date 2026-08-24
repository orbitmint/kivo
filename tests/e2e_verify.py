import sys
import duckdb
import pyarrow as pa
from kivo import KivoEngine, DuckDBExecutor

def main():
    print("Initializing E2E Verification using installed package...")
    
    # 1. Setup in-memory DuckDB table
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
    
    # 2. Setup Kivo Engine and load sales model
    engine = KivoEngine()
    engine.load_model("tests/data/sales_model.yaml")
    
    # 3. Create executor
    executor = DuckDBExecutor(connection=conn)
    
    # 4. Compile and Run Query
    print("Compiling semantic query...")
    sql = engine.compile(
        model_name="sales",
        dimensions=["country"],
        metrics=["total_revenue", "total_orders", "average_order_value"]
    )
    print(f"Compiled SQL:\n{sql}\n")
    
    print("Executing query...")
    result_table = engine.query(
        model_name="sales",
        dimensions=["country"],
        metrics=["total_revenue", "total_orders", "average_order_value"],
        executor=executor
    )
    
    # 5. Assertions
    assert isinstance(result_table, pa.Table), "Result should be a PyArrow Table"
    
    data = result_table.to_pydict()
    print(f"Result Data: {data}")
    
    # Validate CA results
    ca_idx = data["country"].index("CA")
    assert data["total_revenue"][ca_idx] == 200.0
    assert data["total_orders"][ca_idx] == 1
    assert data["average_order_value"][ca_idx] == 200.0
    
    # Validate US results
    us_idx = data["country"].index("US")
    assert data["total_revenue"][us_idx] == 150.0
    assert data["total_orders"][us_idx] == 2
    assert data["average_order_value"][us_idx] == 75.0
    
    print("\n[SUCCESS] E2E Verification Complete! Package is 100% functional.")
    sys.exit(0)

if __name__ == "__main__":
    main()

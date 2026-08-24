import re
import pytest
from kivo.models import Model
from kivo.compiler import SQLCompiler
from kivo.parser import load_model_from_yaml

@pytest.fixture
def sales_model() -> Model:
    return load_model_from_yaml("tests/data/sales_model.yaml")

def clean_sql(sql: str) -> str:
    """Replaces all sequences of whitespace/newlines with a single space and strips."""
    return re.sub(r"\s+", " ", sql).strip()

def test_compiler_base_metrics_only(sales_model):
    compiler = SQLCompiler(dialect="duckdb")
    
    # Run compilation for base metrics and dimensions
    sql = compiler.compile(
        model=sales_model,
        dimensions=["date", "country"],
        metrics=["total_revenue", "total_orders"]
    )
    
    cleaned = clean_sql(sql)
    
    # Assert generated SQL contains expected components and is NOT using a CTE
    assert "WITH" not in sql
    assert "SELECT" in sql
    assert "transaction_date AS date" in cleaned
    assert "customer_country AS country" in cleaned
    assert "SUM(amount) AS total_revenue" in cleaned
    assert "COUNT(order_id) AS total_orders" in cleaned
    assert "FROM raw_sales" in cleaned
    # Check that we group by date and country
    assert "GROUP BY" in cleaned
    assert "date" in cleaned
    assert "country" in cleaned

def test_compiler_with_metric_filter(sales_model):
    compiler = SQLCompiler(dialect="duckdb")
    
    sql = compiler.compile(
        model=sales_model,
        dimensions=["country"],
        metrics=["completed_revenue"]
    )
    
    cleaned = clean_sql(sql)
    
    # Assert conditional aggregation (CASE WHEN) is used for filtered metric
    assert "SUM(CASE WHEN" in cleaned
    assert "status = 'completed'" in cleaned
    assert "THEN amount END) AS completed_revenue" in cleaned

def test_compiler_with_query_filter(sales_model):
    compiler = SQLCompiler(dialect="duckdb")
    
    sql = compiler.compile(
        model=sales_model,
        dimensions=["country"],
        metrics=["total_revenue"],
        filters=["customer_country = 'US'", "amount > 100"]
    )
    
    cleaned = clean_sql(sql)
    
    # Assert query-level WHERE is present
    assert "WHERE" in cleaned
    assert "customer_country = 'US'" in cleaned
    assert "amount > 100" in cleaned

def test_compiler_derived_metric(sales_model):
    compiler = SQLCompiler(dialect="duckdb")
    
    sql = compiler.compile(
        model=sales_model,
        dimensions=["date"],
        metrics=["average_order_value"]
    )
    
    cleaned = clean_sql(sql)
    
    # Assert CTE is used
    assert "WITH kivo_base_metrics AS" in cleaned
    # Base query inside CTE should select base metrics needed: total_revenue and total_orders
    assert "SUM(amount) AS total_revenue" in cleaned
    assert "COUNT(order_id) AS total_orders" in cleaned
    # Outer query should calculate the division and select date, but NOT output base metrics unless explicitly requested
    assert "SELECT" in sql
    assert "date" in cleaned
    assert "total_revenue / total_orders AS average_order_value" in cleaned
    assert "FROM kivo_base_metrics" in cleaned

def test_compiler_derived_metric_explicit_and_implicit(sales_model):
    compiler = SQLCompiler(dialect="duckdb")
    
    # Here, user wants total_revenue explicitly, AND average_order_value (derived)
    sql = compiler.compile(
        model=sales_model,
        dimensions=["date"],
        metrics=["total_revenue", "average_order_value"]
    )
    
    cleaned = clean_sql(sql)
    
    # Assert CTE is used
    assert "WITH kivo_base_metrics AS" in cleaned
    # Outer query must list total_revenue because it was explicitly requested
    assert "total_revenue" in cleaned
    assert "total_revenue / total_orders AS average_order_value" in cleaned

def test_compiler_failures(sales_model):
    compiler = SQLCompiler()
    
    # Non-existent dimension
    with pytest.raises(ValueError, match="Dimension 'unknown_dim' not found"):
        compiler.compile(sales_model, dimensions=["unknown_dim"], metrics=["total_revenue"])
        
    # Non-existent metric
    with pytest.raises(ValueError, match="Metric 'unknown_metric' not found"):
        compiler.compile(sales_model, dimensions=["date"], metrics=["unknown_metric"])

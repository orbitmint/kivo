import pytest
from pydantic import ValidationError
from kivo.models import Model, Dimension, Metric
from kivo.parser import load_model_from_yaml

def test_load_sales_model():
    model = load_model_from_yaml("tests/data/sales_model.yaml")
    
    assert model.name == "sales"
    assert model.table == "raw_sales"
    assert model.sql is None
    assert model.source_sql == "raw_sales"
    
    # Assert dimensions
    assert len(model.dimensions) == 2
    dims = model.dimensions_by_name
    assert "date" in dims
    assert dims["date"].type == "time"
    assert dims["date"].sql_expr == "transaction_date"
    
    assert "country" in dims
    assert dims["country"].type == "categorical"
    assert dims["country"].sql_expr == "customer_country"
    
    # Assert metrics
    assert len(model.metrics) == 5
    metrics = model.metrics_by_name
    assert "total_revenue" in metrics
    assert metrics["total_revenue"].type == "sum"
    assert metrics["total_revenue"].sql_expr == "amount"
    assert len(metrics["total_revenue"].filters) == 0
    
    assert "completed_revenue" in metrics
    assert metrics["completed_revenue"].type == "sum"
    assert metrics["completed_revenue"].sql_expr == "amount"
    assert metrics["completed_revenue"].filters == ["status = 'completed'"]
    
    assert "average_order_value" in metrics
    assert metrics["average_order_value"].type == "derived"
    assert metrics["average_order_value"].sql_expr == "total_revenue / total_orders"

def test_model_validation_failures():
    # Neither table nor sql
    with pytest.raises(ValidationError, match="must specify either 'table' or 'sql'"):
        Model(name="invalid_model", dimensions=[], metrics=[])
        
    # Both table and sql
    with pytest.raises(ValidationError, match="cannot specify both 'table' and 'sql'"):
        Model(
            name="invalid_model",
            table="raw_table",
            sql="SELECT * FROM raw_table",
            dimensions=[],
            metrics=[]
        )

def test_load_ossie_model():
    model = load_model_from_yaml("tests/data/ossie_model.yaml")
    
    assert model.name == "active_customers_revenue_daily"
    assert model.table == "analytics.active_customers_revenue_daily"
    assert model.sql is None
    
    # Assert dimensions
    assert len(model.dimensions) == 3
    dims = model.dimensions_by_name
    assert "country_code" in dims
    assert dims["country_code"].type == "categorical"
    assert "brand" in dims
    assert "created_date" in dims
    assert dims["created_date"].type == "time"
    
    # Assert metrics
    assert len(model.metrics) == 1
    metrics = model.metrics_by_name
    assert "active_customers_revenue_daily" in metrics
    assert metrics["active_customers_revenue_daily"].type == "sum"

def test_load_models_from_directory_with_ossie():
    from kivo.parser import load_models_from_directory
    models = load_models_from_directory("tests/data")
    
    # We should have sales_model (which has 1 model) and ossie_model (which has 1 model)
    assert len(models) == 2
    model_names = [m.name for m in models]
    assert "sales" in model_names
    assert "active_customers_revenue_daily" in model_names

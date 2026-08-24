from typing import List, Set, Dict, Optional
import sqlglot
from sqlglot import exp
from kivo.models.model import Model
from kivo.models.metric import Metric

class SQLCompiler:
    def __init__(self, dialect: Optional[str] = None):
        """
        Initializes the SQLCompiler.
        :param dialect: The default SQLGlot dialect to compile to (e.g., 'duckdb', 'postgres', 'clickhouse', 'bigquery').
        """
        self.dialect = dialect

    def compile(
        self,
        model: Model,
        dimensions: List[str],
        metrics: List[str],
        filters: Optional[List[str]] = None,
        dialect: Optional[str] = None
    ) -> str:
        """
        Compiles a request for dimensions and metrics into a dialect-specific SQL query.
        
        :param model: The Pydantic Model to query.
        :param dimensions: A list of dimension names to group/select by.
        :param metrics: A list of metric names to calculate.
        :param filters: Optional list of SQL filter expressions to apply in the WHERE clause of the base query.
        :param dialect: Override the default dialect for this compilation.
        :return: Transpiled SQL query string.
        """
        target_dialect = dialect or self.dialect
        
        # 1. Validate inputs
        dims_map = model.dimensions_by_name
        metrics_map = model.metrics_by_name

        for dim_name in dimensions:
            if dim_name not in dims_map:
                raise ValueError(f"Dimension '{dim_name}' not found in model '{model.name}'.")

        for metric_name in metrics:
            if metric_name not in metrics_map:
                raise ValueError(f"Metric '{metric_name}' not found in model '{model.name}'.")

        # 2. Resolve metric dependencies recursively
        required_metrics = self._resolve_dependencies(metrics, metrics_map)
        
        # Separate base metrics and derived metrics
        required_base_names: Set[str] = set()
        required_derived_names: Set[str] = set()
        
        for m_name in required_metrics:
            m = metrics_map[m_name]
            if m.type == "derived":
                required_derived_names.add(m_name)
            else:
                required_base_names.add(m_name)

        has_derived = len(required_derived_names) > 0

        # 3. Compile Base Aggregation
        # Base query selects dimensions and base metrics
        base_selects = []
        for d_name in dimensions:
            dim = dims_map[d_name]
            # Select: expression AS alias
            base_selects.append(f"{dim.sql_expr} AS {dim.name}")

        for m_name in required_base_names:
            metric = metrics_map[m_name]
            base_selects.append(f"{self._compile_base_metric(metric)} AS {metric.name}")

        # Build FROM clause
        # If model.sql is provided, it's already parenthesized in source_sql
        from_clause = model.source_sql

        # Build WHERE clause
        where_clause = ""
        if filters:
            combined = " AND ".join(f"({f})" for f in filters)
            where_clause = f" WHERE {combined}"

        # Build GROUP BY clause
        group_clause = ""
        if dimensions:
            # Group by dimension expressions or aliases.
            # Grouping by dimension aliases is widely supported and very clean.
            group_clause = f" GROUP BY " + ", ".join(dimensions)

        base_sql = f"SELECT {', '.join(base_selects)} FROM {from_clause}{where_clause}{group_clause}"

        # 4. Final Query assembly
        if not has_derived:
            # If no derived metrics are needed, the base query is the final query.
            # Parse and transpile using SQLGlot to ensure correctness and formatting.
            parsed = sqlglot.parse_one(base_sql)
            return parsed.sql(dialect=target_dialect, pretty=True)

        # If there are derived metrics, we wrap the base query in a CTE and evaluate derived metrics in the outer select.
        # Outer select must retain original requested order of dimensions and metrics.
        outer_selects = []
        for d_name in dimensions:
            outer_selects.append(d_name)

        for m_name in metrics:
            metric = metrics_map[m_name]
            if metric.type == "derived":
                # The expression of derived metric references other metrics that are selected in the base CTE.
                outer_selects.append(f"{metric.sql_expr} AS {metric.name}")
            else:
                outer_selects.append(metric.name)

        # Assemble with CTE
        cte_name = "kivo_base_metrics"
        final_sql = f"WITH {cte_name} AS ({base_sql}) SELECT {', '.join(outer_selects)} FROM {cte_name}"

        # Transpile final query to target dialect
        parsed = sqlglot.parse_one(final_sql)
        return parsed.sql(dialect=target_dialect, pretty=True)

    def _resolve_dependencies(self, metrics: List[str], metrics_map: Dict[str, Metric]) -> Set[str]:
        """Recursively resolves all metrics and their dependencies."""
        resolved: Set[str] = set()

        def visit(name: str):
            if name in resolved:
                return
            if name not in metrics_map:
                raise ValueError(f"Referenced metric '{name}' does not exist in model.")
            
            metric = metrics_map[name]
            resolved.add(name)
            
            if metric.type == "derived":
                # Find referenced metrics in the expression
                expr_str = metric.sql_expr
                try:
                    parsed_expr = sqlglot.parse_one(expr_str)
                except Exception as e:
                    raise ValueError(f"Failed to parse derived metric expression '{expr_str}' for metric '{name}': {e}")
                
                # Identify all identifiers that correspond to known metrics
                for node in parsed_expr.find_all(exp.Identifier):
                    ref_name = node.name
                    if ref_name in metrics_map:
                        visit(ref_name)

        for m_name in metrics:
            visit(m_name)
        return resolved

    def _compile_base_metric(self, metric: Metric) -> str:
        """Compiles a single non-derived base metric, applying any filters via conditional aggregation."""
        expr = metric.sql_expr
        
        # Apply filters inside the aggregate function using CASE WHEN (conditional aggregation)
        if metric.filters:
            combined_filters = " AND ".join(f"({f})" for f in metric.filters)
            expr = f"CASE WHEN {combined_filters} THEN {expr} END"

        m_type = metric.type.lower()
        if m_type == "sum":
            return f"SUM({expr})"
        elif m_type == "avg":
            return f"AVG({expr})"
        elif m_type == "count":
            return f"COUNT({expr})"
        elif m_type in ("count_distinct", "count distinct"):
            return f"COUNT(DISTINCT {expr})"
        elif m_type == "min":
            return f"MIN({expr})"
        elif m_type == "max":
            return f"MAX({expr})"
        else:
            raise ValueError(f"Unsupported base metric type '{metric.type}' for metric '{metric.name}'.")

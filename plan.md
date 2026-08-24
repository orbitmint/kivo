1 # Semantic Layer MVP (Kivo) Architecture Plan
    2
    3 ## 1. Objective
    4 Build a Python-based open-source semantic layer MVP (inspired by Dosi). It will parse an Open Semantic Interchange (OSI) inspired YAML schema,
      compile it into native SQL using an AST, and execute queries across BigQuery, PostgreSQL, ClickHouse, and DuckDB. The project must be structured
      for immediate publishing to PyPI.
    5
    6 ## 2. Proposed Architecture vs. Dosi
    7
    8 Our proposed architecture takes a pragmatic, open-source-first approach:
    9
   10 1.  **Core Language:** Written in **Python** (Dosi uses Rust). Python is the standard for data engineering, allows for rapid iteration, and has
      excellent libraries for parsing and AST manipulation.
   11 2.  **SQL Transpilation Engine:** Leverages **SQLGlot** (Dosi uses a proprietary engine). SQLGlot is a pure-Python SQL parser and transpiler that
      allows us to build an Abstract Syntax Tree (AST) representing the metric calculation and compile it safely into multiple dialects.
   12 3.  **Open Source vs Proprietary:** Fully transparent Python source code that you control and can extend (Dosi is closed-source).
   13 4.  **Performance Trade-offs:** Python adds minor overhead to parsing and SQL compilation, but for *execution*, we achieve high performance by
      utilizing `PyArrow` natively within the execution layers (specifically for DuckDB and BigQuery) to stream the resulting datasets efficiently.
   14
   15 ## 3. Core Components
   16 1. **Model Parser (`parser.py`)**: Uses `PyYAML` and `Pydantic` to parse and validate YAML metric files based on the OSI specification.
   17 2. **SQL Compiler (`compiler.py`)**: Uses **SQLGlot** to build and transpile the query AST. Handles fan-out protection and metric algebra.
   18 3. **Execution Engine (`executors/`)**: Manages connections to the target databases and handles zero-copy Arrow streaming where supported.
   19 4. **Core Interface (`engine.py`)**: The programmatic entry point that orchestrates parsing, compiling, and executing.
   20
   21 ## 4. Directory Structure
  kivo/
  ├── pyproject.toml             # Configured for PyPI publishing
  ├── src/
  │   ├── kivo/
  │   │   ├── __init__.py
  │   │   ├── models/            # Pydantic schemas for the OSI YAML format
  │   │   │   ├── model.py       # Table/View definitions
  │   │   │   ├── metric.py      # Metric calculations (SUM, AVG, custom)
  │   │   │   └── dimension.py   # Dimensions (group bys)
  │   │   ├── compiler/          # SQLGlot AST generation logic
  │   │   │   └── sql_builder.py
  │   │   ├── executors/         # Database connection layers
  │   │   │   ├── base.py
  │   │   │   ├── duckdb_exec.py
  │   │   │   ├── postgres_exec.py
  │   │   │   ├── bigquery_exec.py
  │   │   │   └── clickhouse_exec.py
   1
   2 ## 5. Next Steps for Implementation
   3 1. Initialize the directory with this structure.
   4 2. Write the `pyproject.toml` with necessary dependencies (`sqlglot`, `pydantic`, `pyarrow`, db drivers) and PyPI metadata.
   5 3. Implement Phase 1: The Pydantic models for parsing.
   6 4. Implement Phase 2: The SQLGlot translation layer.
   7 5. Implement Phase 3: The database executors.

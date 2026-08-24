import duckdb
import pyarrow as pa
from kivo.executors.base import BaseExecutor

class DuckDBExecutor(BaseExecutor):
    def __init__(self, db_path: str = ":memory:", connection=None):
        """
        Initializes the DuckDBExecutor.
        
        :param db_path: Path to the DuckDB file, or ':memory:'.
        :param connection: An existing duckdb.DuckDBPyConnection instance (optional).
        """
        self.should_close = False
        if connection is not None:
            self.conn = connection
        else:
            self.conn = duckdb.connect(db_path)
            self.should_close = True

    def execute_query(self, sql: str) -> pa.Table:
        """Executes query and streams result as PyArrow Table natively."""
        res = self.conn.execute(sql).arrow()
        if isinstance(res, pa.RecordBatchReader):
            return res.read_all()
        return res

    def close(self) -> None:
        if self.should_close and self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

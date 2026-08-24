import psycopg2
import pyarrow as pa
from kivo.executors.base import BaseExecutor

class PostgreSQLExecutor(BaseExecutor):
    def __init__(self, connection=None, **conn_kwargs):
        """
        Initializes the PostgreSQLExecutor.
        
        :param connection: An existing psycopg2 connection instance (optional).
        :param conn_kwargs: Key-value arguments passed directly to psycopg2.connect.
        """
        self.should_close = False
        if connection is not None:
            self.conn = connection
        else:
            self.conn = psycopg2.connect(**conn_kwargs)
            self.should_close = True

    def execute_query(self, sql: str) -> pa.Table:
        """Executes a query against PostgreSQL and returns results as a PyArrow Table."""
        with self.conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            names = [desc[0] for desc in cursor.description] if cursor.description else []
            
            if not names:
                return pa.Table.from_arrays([], names=[])
                
            if not rows:
                return pa.Table.from_arrays([pa.array([]) for _ in names], names=names)
                
            columns = list(zip(*rows))
            arrays = [pa.array(col) for col in columns]
            return pa.Table.from_arrays(arrays, names=names)

    def close(self) -> None:
        if self.should_close and self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

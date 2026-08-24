import clickhouse_connect
import pyarrow as pa
from kivo.executors.base import BaseExecutor

class ClickHouseExecutor(BaseExecutor):
    def __init__(self, client=None, **client_kwargs):
        """
        Initializes the ClickHouseExecutor.
        
        :param client: An existing clickhouse_connect Client instance (optional).
        :param client_kwargs: Key-value arguments passed directly to clickhouse_connect.get_client.
        """
        self.should_close = False
        if client is not None:
            self.client = client
        else:
            self.client = clickhouse_connect.get_client(**client_kwargs)
            self.should_close = True

    def execute_query(self, sql: str) -> pa.Table:
        """Executes a query against ClickHouse and returns results as a PyArrow Table."""
        # clickhouse_connect natively supports query_arrow which returns a pyarrow.Table
        return self.client.query_arrow(sql)

    def close(self) -> None:
        if self.should_close and self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None

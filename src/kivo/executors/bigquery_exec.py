from google.cloud import bigquery
import pyarrow as pa
from kivo.executors.base import BaseExecutor

class BigQueryExecutor(BaseExecutor):
    def __init__(self, client=None, **client_kwargs):
        """
        Initializes the BigQueryExecutor.
        
        :param client: An existing google.cloud.bigquery.Client instance (optional).
        :param client_kwargs: Key-value arguments passed directly to bigquery.Client.
        """
        self.should_close = False
        if client is not None:
            self.client = client
        else:
            self.client = bigquery.Client(**client_kwargs)
            self.should_close = True

    def execute_query(self, sql: str) -> pa.Table:
        """Executes query against BigQuery and streams results as a PyArrow Table."""
        query_job = self.client.query(sql)
        return query_job.to_arrow()

    def close(self) -> None:
        if self.should_close and self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None

from abc import ABC, abstractmethod
import pyarrow as pa

class BaseExecutor(ABC):
    @abstractmethod
    def execute_query(self, sql: str) -> pa.Table:
        """
        Executes a SQL query and returns the results as a PyArrow Table.
        
        :param sql: The compiled SQL query string to run.
        :return: A pyarrow.Table containing the query results.
        """
        pass

    def close(self) -> None:
        """Optional hook to release connection resources."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

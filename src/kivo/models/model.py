from typing import Optional, List, Dict
from pydantic import BaseModel, Field, model_validator
from kivo.models.dimension import Dimension
from kivo.models.metric import Metric

class Model(BaseModel):
    name: str
    table: Optional[str] = Field(default=None, description="Physical database table name.")
    sql: Optional[str] = Field(default=None, description="Inline subquery to serve as the source.")
    dimensions: List[Dimension] = Field(default_factory=list)
    metrics: List[Metric] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source(self) -> 'Model':
        if not self.table and not self.sql:
            raise ValueError(f"Model '{self.name}' must specify either 'table' or 'sql' as a source.")
        if self.table and self.sql:
            raise ValueError(f"Model '{self.name}' cannot specify both 'table' and 'sql' as sources.")
        return self

    @property
    def source_sql(self) -> str:
        """Returns either the physical table name or the wrapped subquery."""
        if self.table:
            return self.table
        return f"({self.sql})"

    @property
    def dimensions_by_name(self) -> Dict[str, Dimension]:
        return {d.name: d for d in self.dimensions}

    @property
    def metrics_by_name(self) -> Dict[str, Metric]:
        return {m.name: m for m in self.metrics}

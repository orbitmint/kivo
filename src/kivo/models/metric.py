from typing import Optional, List
from pydantic import BaseModel, Field

class Metric(BaseModel):
    name: str
    type: str = Field(description="Calculation type (e.g., sum, avg, count, count_distinct, min, max, derived)")
    expr: Optional[str] = Field(default=None, description="SQL expression or derived formula.")
    filters: List[str] = Field(default_factory=list, description="Filter expressions applied only to this metric.")

    @property
    def sql_expr(self) -> str:
        if self.expr is not None:
            return self.expr
        if self.type == "count":
            return "*"
        return self.name

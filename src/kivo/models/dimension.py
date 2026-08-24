from typing import Optional
from pydantic import BaseModel, Field

class Dimension(BaseModel):
    name: str
    type: str = Field(description="Type of the dimension (e.g., categorical, time, numerical)")
    expr: Optional[str] = Field(default=None, description="SQL expression. Defaults to name if not provided.")

    @property
    def sql_expr(self) -> str:
        return self.expr if self.expr is not None else self.name

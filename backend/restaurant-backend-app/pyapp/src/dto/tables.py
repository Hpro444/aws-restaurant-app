"""DTOs for table-related responses."""

from pydantic import BaseModel, ConfigDict


class TableDTO(BaseModel):
    """Table data returned to waiters."""

    model_config = ConfigDict(extra="ignore")

    table_number: int

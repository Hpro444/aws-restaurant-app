"""DTOs for the GET /customers endpoint."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CustomerResponse(BaseModel):
    """One customer item returned by GET /customers."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    user_name: str
    email: str

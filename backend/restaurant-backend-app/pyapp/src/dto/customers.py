"""DTOs for the GET /customers endpoint."""

from pydantic import BaseModel, ConfigDict


class CustomerResponse(BaseModel):
    """One customer item returned by GET /customers."""

    model_config = ConfigDict(extra="ignore")

    user_name: str
    email: str

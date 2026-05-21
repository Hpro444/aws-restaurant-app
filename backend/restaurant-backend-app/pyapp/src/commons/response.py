"""Lambda proxy integration response model."""

from pydantic import BaseModel, ConfigDict, Field


class LambdaResponse(BaseModel):
    """Represents an AWS Lambda proxy integration response."""

    model_config = ConfigDict(extra="ignore")

    statusCode: int
    headers: dict[str, str] = Field(
        default_factory=lambda: {"Content-Type": "application/json"}
    )
    body: str

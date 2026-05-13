"""Lambda proxy integration response model."""

from pydantic import BaseModel, Field


class LambdaResponse(BaseModel):
    """Represents an AWS Lambda proxy integration response."""

    statusCode: int
    headers: dict[str, str] = Field(
        default_factory=lambda: {"Content-Type": "application/json"}
    )
    body: str

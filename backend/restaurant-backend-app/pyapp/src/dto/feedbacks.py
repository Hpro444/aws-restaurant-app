"""DTOs for GET /locations/{id}/feedbacks responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeedbackResponse(BaseModel):
    """A single feedback item returned by the feedbacks endpoint."""

    model_config = ConfigDict(extra="ignore")

    id: str
    customer_id: str | None = None
    feedback: str
    rate: int | None = None
    date: datetime
    user_name: str | None = None
    user_image_url: str | None = None
    location_id: str | None = None
    waiter_id: str | None = None


class FeedbackPageableResponse(BaseModel):
    """Pagination metadata returned under the pageable node."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    offset: int
    sort: list[str]
    paged: bool
    page_size: int = Field(..., alias="pageSize")
    page_number: int = Field(..., alias="pageNumber")
    unpaged: bool


class PageFeedbackResponse(BaseModel):
    """Paginated feedback response wrapper for GET /locations/{id}/feedbacks."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    total_pages: int = Field(..., alias="totalPages")
    total_elements: int = Field(..., alias="totalElements")
    size: int
    content: list[FeedbackResponse]
    number: int
    sort: list[str]
    first: bool
    last: bool
    number_of_elements: int = Field(..., alias="numberOfElements")
    pageable: FeedbackPageableResponse
    empty: bool

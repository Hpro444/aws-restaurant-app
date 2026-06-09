"""DTOs for feedback read and create endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from enums import FeedbackType
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
)


class LeaveFeedbackRequest(BaseModel):
    """Validated body for POST /feedbacks/."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )

    reservation_id: UUID = Field(
        ...,
    )
    type: FeedbackType
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value: object) -> object:
        """Accept legacy 'cuisine' input and map it to 'culinary'."""
        if isinstance(value, str) and value.strip().lower() == "cuisine":
            return FeedbackType.CULINARY
        return value

    @field_validator("rating", mode="before")
    @classmethod
    def coerce_rating(cls, value: object) -> object:
        """Allow numeric-string ratings while keeping integer validation strict."""
        if isinstance(value, str) and value.strip():
            try:
                return int(value)
            except ValueError:
                return value
        return value

    @field_validator("comment")
    @classmethod
    def normalize_comment(
        cls,
        value: str | None,
        info: ValidationInfo,
    ) -> str:
        """Store an empty comment when omitted to fit feedback domain schema."""
        if value is None:
            return ""
        return value.strip()


class LeaveFeedbackResponse(BaseModel):
    """Simple success payload for feedback creation."""

    model_config = ConfigDict(extra="ignore")

    message: str


class FeedbackContextResponse(BaseModel):
    """Modal context payload for feedback creation UI."""

    model_config = ConfigDict(extra="ignore")

    reservation_id: str
    waiter_id: str | None = None
    waiter_name: str | None = None
    waiter_image_url: str | None = None


class UpdateFeedbackRequest(BaseModel):
    """Validated body for PUT /feedbacks/."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )

    reservation_id: UUID = Field(...)
    type: FeedbackType
    rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = None

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value: object) -> object:
        """Accept legacy 'cuisine' input and map it to 'culinary'."""
        if isinstance(value, str) and value.strip().lower() == "cuisine":
            return FeedbackType.CULINARY
        return value

    @field_validator("rating", mode="before")
    @classmethod
    def coerce_rating(cls, value: object) -> object:
        """Allow numeric-string ratings while keeping integer validation strict."""
        if isinstance(value, str) and value.strip():
            try:
                return int(value)
            except ValueError:
                return value
        return value


class UpdateFeedbackResponse(BaseModel):
    """Simple success payload for feedback update."""

    model_config = ConfigDict(extra="ignore")

    message: str


class GetFeedbacksRequest(BaseModel):
    """Validated query params for GET /locations/{id}/feedbacks."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    type: str
    sort: str = "date,desc"
    page: int = Field(0, ge=0)
    size: int = Field(20, ge=1, le=100)

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        """Allow only supported feedback type filters."""
        if value not in {"cuisine", "service"}:
            raise ValueError("Must be one of: cuisine, service")
        return value

    @field_validator("sort")
    @classmethod
    def validate_sort(cls, value: str) -> str:
        """Validate sort key and optional direction token."""
        sort_key, _, sort_direction = value.partition(",")
        if sort_key not in {"date", "rate"}:
            raise ValueError("Sort field must be one of: date, rate")
        if sort_direction and sort_direction not in {"asc", "desc"}:
            raise ValueError("Sort direction must be one of: asc, desc")
        return value


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

"""Service for retrieving location feedback with filtering and pagination."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from repositories.feedback_cuisine_repository import FeedbackCuisineRepository
from repositories.feedback_service_repository import FeedbackServiceRepository


class FeedbackService:
    """Application service for cuisine/service feedback retrieval."""

    def __init__(
        self,
        feedback_cuisine_repo: FeedbackCuisineRepository | None = None,
        feedback_service_repo: FeedbackServiceRepository | None = None,
    ) -> None:
        """Initialize repositories, creating defaults when omitted."""
        self._feedback_cuisine_repo = (
            feedback_cuisine_repo or FeedbackCuisineRepository()
        )
        self._feedback_service_repo = (
            feedback_service_repo or FeedbackServiceRepository()
        )

    def get_feedbacks(
        self,
        location_id: UUID,
        type: str,
        sort: list[str],
        page: int,
        size: int,
    ) -> dict[str, Any]:
        """Retrieve feedbacks by location and type with sorting and pagination."""
        if type == "cuisine":
            feedbacks = self._feedback_cuisine_repo.find_by_location_id(location_id)
        elif type == "service":
            feedbacks = self._feedback_service_repo.find_by_location_id(location_id)
        else:
            raise ValueError("Invalid feedback type")

        for criterion in reversed(sort):
            key, _, direction = criterion.partition(",")
            feedbacks.sort(
                key=lambda feedback: getattr(feedback, key),
                reverse=(direction == "desc"),
            )

        start = page * size
        end = start + size
        paged_feedbacks = feedbacks[start:end]

        return {
            "totalPages": (len(feedbacks) + size - 1) // size,
            "totalElements": len(feedbacks),
            "size": size,
            "content": paged_feedbacks,
            "number": page,
            "sort": sort,
            "first": page == 0,
            "last": end >= len(feedbacks),
            "numberOfElements": len(paged_feedbacks),
            "pageable": {
                "offset": start,
                "sort": sort,
                "paged": True,
                "pageSize": size,
                "pageNumber": page,
                "unpaged": False,
            },
            "empty": not paged_feedbacks,
        }

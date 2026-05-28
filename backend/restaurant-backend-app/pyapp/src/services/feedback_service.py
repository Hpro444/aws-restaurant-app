"""Service for retrieving location feedback with filtering and pagination."""

from __future__ import annotations

from uuid import UUID

from commons.log_helper import logger
from domain.feedback import Feedback
from dto.feedbacks import (
    FeedbackPageableResponse,
    FeedbackResponse,
    PageFeedbackResponse,
)
from repositories.customer_repository import CustomerRepository
from repositories.feedback_cuisine_repository import FeedbackCuisineRepository
from repositories.feedback_service_repository import FeedbackServiceRepository


class FeedbackService:
    """Application service for cuisine/service feedback retrieval."""

    def __init__(
        self,
        feedback_cuisine_repo: FeedbackCuisineRepository | None = None,
        feedback_service_repo: FeedbackServiceRepository | None = None,
        customer_repo: CustomerRepository | None = None,
    ) -> None:
        """Initialize repositories, creating defaults when omitted."""
        self._feedback_cuisine_repo = (
            feedback_cuisine_repo or FeedbackCuisineRepository()
        )
        self._feedback_service_repo = (
            feedback_service_repo or FeedbackServiceRepository()
        )
        self._customer_repo = customer_repo or CustomerRepository()

    def get_feedbacks(
        self,
        location_id: UUID,
        type: str,
        sort: list[str],
        page: int,
        size: int,
    ) -> PageFeedbackResponse:
        """Retrieve feedbacks by location and type with sorting and pagination."""
        logger.info(
            "Retrieving feedbacks",
            location_id=str(location_id),
            feedback_type=type,
            sort=sort,
            page=page,
            size=size,
        )

        if type == "cuisine":
            feedbacks = self._feedback_cuisine_repo.find_by_location_id(location_id)
        elif type == "service":
            feedbacks = self._feedback_service_repo.find_by_location_id(location_id)
        else:
            raise ValueError("Invalid feedback type")

        logger.info(
            "Feedbacks retrieved from repository",
            location_id=str(location_id),
            feedback_type=type,
            total_found=len(feedbacks),
        )

        for criterion in reversed(sort):
            key, _, direction = criterion.partition(",")
            feedbacks.sort(
                key=lambda feedback: getattr(feedback, key),
                reverse=(direction == "desc"),
            )

        start = page * size
        end = start + size
        paged_feedbacks = feedbacks[start:end]

        content = [
            self._build_feedback_response(feedback) for feedback in paged_feedbacks
        ]

        response = PageFeedbackResponse(
            totalPages=(len(feedbacks) + size - 1) // size,
            totalElements=len(feedbacks),
            size=size,
            content=content,
            number=page,
            sort=sort,
            first=page == 0,
            last=end >= len(feedbacks),
            numberOfElements=len(content),
            pageable=FeedbackPageableResponse(
                offset=start,
                sort=sort,
                paged=True,
                pageSize=size,
                pageNumber=page,
                unpaged=False,
            ),
            empty=not content,
        )

        logger.info(
            "Feedback page built",
            location_id=str(location_id),
            feedback_type=type,
            returned_count=len(content),
            total_elements=response.total_elements,
            total_pages=response.total_pages,
            page=page,
        )
        return response

    def _build_feedback_response(
        self,
        feedback: Feedback,
    ) -> FeedbackResponse:
        """Map a feedback domain object to API response shape with user enrichment."""
        user_name = feedback.user_name
        user_image_url = feedback.user_image_url

        if feedback.customer_id is not None:
            customer_name, customer_image_url = self._get_customer_profile(
                feedback.customer_id
            )
            user_name = customer_name
            user_image_url = customer_image_url or user_image_url

        location_id = getattr(feedback, "location_id", None)
        waiter_id = getattr(feedback, "waiter_id", None)

        return FeedbackResponse(
            id=str(feedback.id),
            customer_id=(
                str(feedback.customer_id) if feedback.customer_id is not None else None
            ),
            feedback=feedback.feedback,
            rate=feedback.rate,
            date=feedback.date,
            user_name=user_name,
            user_image_url=user_image_url,
            location_id=str(location_id) if location_id is not None else None,
            waiter_id=str(waiter_id) if waiter_id is not None else None,
        )

    def _get_customer_profile(
        self,
        customer_id: UUID,
    ) -> tuple[str | None, str | None]:
        """Return customer display name and avatar URL."""
        customer = self._customer_repo.get(customer_id)
        if customer is None:
            logger.warning(
                "Customer profile not found for feedback",
                customer_id=str(customer_id),
            )
            return (None, None)

        full_name = f"{customer.fname} {customer.lname}".strip()
        return (full_name or None, customer.image_url)

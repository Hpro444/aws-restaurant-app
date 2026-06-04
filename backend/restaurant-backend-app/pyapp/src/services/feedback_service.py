"""Service for retrieving location feedback with filtering and pagination."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from commons.exceptions import ApplicationException
from commons.log_helper import logger
from commons.uuid_utils import coerce_uuid
from domain.feedback import Feedback, FeedbackCuisine
from domain.feedback import FeedbackService as ServiceFeedback
from domain.reservation import Reservation
from dto.feedbacks import (
    FeedbackPageableResponse,
    FeedbackResponse,
    LeaveFeedbackRequest,
    PageFeedbackResponse,
)
from enums.feedback_type import FeedbackType
from enums.http_status_code import HttpStatusCode
from enums.reservation_status import ReservationStatus
from repositories.customer_repository import CustomerRepository
from repositories.feedback_cuisine_repository import FeedbackCuisineRepository
from repositories.feedback_service_repository import FeedbackServiceRepository
from repositories.reservation_repository import ReservationRepository
from repositories.slot_repository import SlotRepository
from repositories.table_repository import TableRepository


class FeedbackService:
    """Application service for cuisine/service feedback retrieval."""

    def __init__(
        self,
        feedback_cuisine_repo: FeedbackCuisineRepository | None = None,
        feedback_service_repo: FeedbackServiceRepository | None = None,
        customer_repo: CustomerRepository | None = None,
        reservation_repo: ReservationRepository | None = None,
        slot_repo: SlotRepository | None = None,
        table_repo: TableRepository | None = None,
    ) -> None:
        """Initialize repositories, creating defaults when omitted."""
        self._feedback_cuisine_repo = (
            feedback_cuisine_repo or FeedbackCuisineRepository()
        )
        self._feedback_service_repo = (
            feedback_service_repo or FeedbackServiceRepository()
        )
        self._customer_repo = customer_repo or CustomerRepository()
        self._reservation_repo = reservation_repo or ReservationRepository()
        self._slot_repo = slot_repo or SlotRepository()
        self._table_repo = table_repo or TableRepository()

    def leave_feedback(
        self,
        request: LeaveFeedbackRequest,
        customer_id: UUID | str,
    ) -> None:
        """Create a cuisine or service feedback row for the authenticated customer."""
        customer_uuid = coerce_uuid(customer_id)
        reservation = self._reservation_repo.get(request.reservation_id)

        if reservation is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Reservation not found",
            )

        if reservation.customer_id != customer_uuid:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Customers can leave feedback only for their own reservations.",
            )

        self._validate_feedback_eligibility(request.type, reservation.status)

        if request.type == FeedbackType.SERVICE:
            self._create_service_feedback(request, reservation, customer_uuid)
            return

        self._create_culinary_feedback(request, reservation, customer_uuid)

    @staticmethod
    def _validate_feedback_eligibility(
        feedback_type: FeedbackType,
        reservation_status: ReservationStatus,
    ) -> None:
        """Ensure feedback can be submitted only for allowed reservation statuses."""
        # Ukoliko je rezervacija IN_PROGRESS, dozvoljeno je ostaviti SERVICE feedback.
        # Ukoliko je rezervacija FINISHED, dozvoljeno je ostaviti i CULINARY i SERVICE feedback.

        if feedback_type == FeedbackType.SERVICE and reservation_status not in {
            ReservationStatus.IN_PROGRESS,
            ReservationStatus.FINISHED,
        }:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                "Service feedback is allowed only when reservation is IN_PROGRESS or FINISHED.",
            )

        if (
            feedback_type == FeedbackType.CULINARY
            and reservation_status != ReservationStatus.FINISHED
        ):
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                "Culinary feedback is allowed only when reservation is FINISHED.",
            )

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

    def _create_service_feedback(
        self,
        request: LeaveFeedbackRequest,
        reservation: Reservation,
        customer_id: UUID,
    ) -> None:
        """Persist service feedback by using waiter_id resolved from reservation."""
        waiter_id = reservation.waiter_id
        if waiter_id is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                "Reservation is not assigned to a waiter.",
            )

        user_name, user_image_url = self._get_customer_profile(customer_id)

        feedback_id = uuid5(NAMESPACE_URL, f"service:{request.reservation_id}")
        try:
            self._feedback_service_repo.create(
                ServiceFeedback(
                    id=feedback_id,
                    reservation_id=reservation.id,
                    customer_id=customer_id,
                    user_name=user_name,
                    user_image_url=user_image_url,
                    feedback=request.comment or "",
                    rate=request.rating,
                    date=datetime.now(UTC),
                    waiter_id=waiter_id,
                )
            )
        except ApplicationException as exc:
            if exc.code == 409:
                raise ApplicationException(
                    HttpStatusCode.RESPONSE_CONFLICT_CODE,
                    "Service feedback for this reservation has already been submitted.",
                ) from exc
            raise

    def _create_culinary_feedback(
        self,
        request: LeaveFeedbackRequest,
        reservation: Reservation,
        customer_id: UUID,
    ) -> None:
        """Persist culinary feedback by resolving reservation location from slots."""
        location_id = self._resolve_location_id_for_reservation(reservation)
        user_name, user_image_url = self._get_customer_profile(customer_id)

        feedback_id = uuid5(NAMESPACE_URL, f"culinary:{request.reservation_id}")
        try:
            self._feedback_cuisine_repo.create(
                FeedbackCuisine(
                    id=feedback_id,
                    reservation_id=reservation.id,
                    customer_id=customer_id,
                    user_name=user_name,
                    user_image_url=user_image_url,
                    feedback=request.comment or "",
                    rate=request.rating,
                    date=datetime.now(UTC),
                    location_id=location_id,
                )
            )
        except ApplicationException as exc:
            if exc.code == 409:
                raise ApplicationException(
                    HttpStatusCode.RESPONSE_CONFLICT_CODE,
                    "Culinary feedback for this reservation has already been submitted.",
                ) from exc
            raise

    def _resolve_location_id_for_reservation(self, reservation: Reservation) -> UUID:
        """Resolve reservation location using the first slot's table."""
        if not reservation.slot_ids:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                "Reservation has no slots.",
            )

        slots = self._slot_repo.find_by_ids(reservation.slot_ids)
        if not slots:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                "Reservation slots not found.",
            )

        table = self._table_repo.get(slots[0].table_id)
        if table is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                "Reservation location could not be resolved.",
            )
        return table.location_id

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

        fname = getattr(customer, "fname", None)
        lname = getattr(customer, "lname", None)
        image_url = getattr(customer, "image_url", None)

        full_name = " ".join(part for part in [fname, lname] if part).strip()
        return (full_name or None, image_url)

"""Service for retrieving location feedback with filtering and pagination."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from commons.app_config import AppConfig
from commons.exceptions import ApplicationException
from commons.log_helper import logger
from commons.uuid_utils import coerce_uuid
from domain.feedback import Feedback, FeedbackCuisine
from domain.feedback import FeedbackService as ServiceFeedback
from domain.reservation import Reservation
from dto.feedback_event import FeedbackEventMessage, FeedbackEventType
from dto.feedbacks import (
    FeedbackContextResponse,
    FeedbackPageableResponse,
    FeedbackResponse,
    LeaveFeedbackRequest,
    PageFeedbackResponse,
    UpdateFeedbackRequest,
)
from enums import FeedbackType, HttpStatusCode, ReservationStatus
from repositories.customer_repository import CustomerRepository
from repositories.feedback_cuisine_repository import FeedbackCuisineRepository
from repositories.feedback_service_repository import FeedbackServiceRepository
from repositories.location_repository import LocationRepository
from repositories.reservation_repository import ReservationRepository
from repositories.slot_repository import SlotRepository
from repositories.table_repository import TableRepository
from repositories.waiter_report_repository import WaiterReportRepository
from repositories.waiter_repository import WaiterRepository

from services.sqs_service import SqsService


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
        location_repo: LocationRepository | None = None,
        waiter_repo: WaiterRepository | None = None,
        waiter_report_repo: WaiterReportRepository | None = None,
        sqs_service: SqsService | None = None,
        settings: AppConfig | None = None,
    ) -> None:
        """Initialize repositories, creating defaults when omitted."""
        cfg = settings or AppConfig()
        self._settings = cfg
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
        self._location_repo = location_repo or LocationRepository()
        self._waiter_repo = waiter_repo or WaiterRepository()
        self._waiter_report_repo = waiter_report_repo or WaiterReportRepository()
        self._sqs = sqs_service

    def get_feedback_context(
        self,
        reservation_id: UUID | str,
        customer_id: UUID | str,
    ) -> FeedbackContextResponse:
        """Return minimal waiter context needed by feedback modal for one reservation."""
        reservation_uuid = coerce_uuid(reservation_id)
        customer_uuid = coerce_uuid(customer_id)
        reservation = self._reservation_repo.get(reservation_uuid)

        if reservation is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Reservation not found",
            )

        if reservation.customer_id != customer_uuid:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Customers can access feedback context only for their own reservations.",
            )

        waiter_id = reservation.waiter_id
        if waiter_id is None:
            return FeedbackContextResponse(reservation_id=str(reservation.id))

        waiter = self._waiter_repo.get(waiter_id)
        if waiter is None:
            return FeedbackContextResponse(
                reservation_id=str(reservation.id),
                waiter_id=str(waiter_id),
            )

        waiter_name = f"{waiter.fname} {waiter.lname}".strip()
        avg_rating = self._calculate_waiter_avg_rating(waiter.id)
        # TODO: privremeni logger
        logger.info(
            "Waiter context resolved for feedback",
            reservation_id=str(reservation.id),
            waiter_id=str(waiter.id),
            waiter_name=waiter_name,
            waiter_avg_rating=avg_rating,
        )
        return FeedbackContextResponse(
            reservation_id=str(reservation.id),
            waiter_id=str(waiter.id),
            waiter_name=waiter_name or None,
            waiter_image_url=waiter.image_url,
            waiter_avg_rating=avg_rating,
        )

    def get_feedbacks_by_reservation_id(
        self,
        reservation_id: UUID | str,
        customer_id: UUID | str,
    ) -> dict:
        """Return all feedbacks (service and/or cuisine) tied to a reservation.

        Only the customer who owns the reservation can access its feedbacks.
        Returns a dict with CuisineFeedback and ServiceFeedback keys (may be None).
        """
        reservation_uuid = coerce_uuid(reservation_id)
        customer_uuid = coerce_uuid(customer_id)

        logger.info(
            "Retrieving feedbacks by reservation",
            reservation_id=str(reservation_uuid),
            customer_id=str(customer_uuid),
        )

        # Validate reservation ownership
        reservation = self._reservation_repo.get(reservation_uuid)
        if reservation is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Reservation not found",
            )

        if reservation.customer_id != customer_uuid:
            logger.warning(
                "Unauthorized reservation feedbacks access attempt",
                reservation_id=str(reservation_uuid),
                requested_by=str(customer_uuid),
                owner_customer_id=str(reservation.customer_id),
            )
            raise ApplicationException(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Not authorized to access feedbacks for this reservation.",
            )

        # Fetch both types of feedback
        cuisine_feedbacks = self._feedback_cuisine_repo.find_by_reservation_id(
            reservation_uuid
        )
        service_feedbacks = self._feedback_service_repo.find_by_reservation_id(
            reservation_uuid
        )

        # Build response dict
        cuisine_response = None
        if cuisine_feedbacks:
            cuisine_response = self._build_feedback_response(
                cuisine_feedbacks[0]
            ).model_dump(mode="json")

        service_response = None
        if service_feedbacks:
            service_response = self._build_feedback_response(
                service_feedbacks[0]
            ).model_dump(mode="json")

        response = {
            "CuisineFeedback": cuisine_response,
            "ServiceFeedback": service_response,
        }

        logger.info(
            "Feedbacks retrieved by reservation",
            reservation_id=str(reservation_uuid),
            customer_id=str(customer_uuid),
            has_cuisine_feedback=cuisine_response is not None,
            has_service_feedback=service_response is not None,
        )

        return response

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

        self._validate_leave_eligibility(reservation.status)

        if request.type == FeedbackType.SERVICE:
            self._create_service_feedback(request, reservation, customer_uuid)
        else:
            self._create_culinary_feedback(request, reservation, customer_uuid)

        if reservation.status != ReservationStatus.FINISHED:
            reservation.status = ReservationStatus.FINISHED
            self._reservation_repo.update(reservation)

    def update_feedback(
        self,
        request: UpdateFeedbackRequest,
        customer_id: UUID | str,
    ) -> bool:
        """Update an existing feedback row for the authenticated customer."""
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
                "Customers can edit feedback only for their own reservations.",
            )

        self._validate_update_eligibility(reservation.status)

        if request.type == FeedbackType.SERVICE:
            return self._update_service_feedback(request, customer_uuid)

        return self._update_culinary_feedback(request, customer_uuid)

    @staticmethod
    def _feedback_date_for(reservation: Reservation) -> datetime:
        """Return the datetime feedback should be attributed to.

        Feedback is attributed to the week the meal took place (the reservation's
        dining date), consistent with how orders and revenue are aggregated into
        the weekly reports, rather than the moment the review happened to be
        submitted. This keeps a single reservation's orders, revenue, and feedback
        in the same weekly report even when the review is left on a later day.

        Falls back to the current time when the reservation carries no date.
        """
        if reservation.date:
            return datetime.fromisoformat(f"{reservation.date}T00:00:00+00:00")
        return datetime.now(UTC)

    @staticmethod
    def _validate_leave_eligibility(reservation_status: ReservationStatus) -> None:
        """Ensure feedback can be posted only when reservation is IN_PROGRESS or FINISHED."""
        if reservation_status not in {
            ReservationStatus.IN_PROGRESS,
            ReservationStatus.FINISHED,
        }:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                "Feedback can be posted only when reservation is IN_PROGRESS or FINISHED.",
            )

    @staticmethod
    def _validate_update_eligibility(reservation_status: ReservationStatus) -> None:
        """Ensure feedback can be edited only when reservation is FINISHED."""
        if reservation_status != ReservationStatus.FINISHED:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_UNPROCESSABLE_ENTITY,
                "Feedback can be edited only when reservation is FINISHED.",
            )

    def _calculate_waiter_avg_rating(self, waiter_id: UUID) -> float | None:
        """Calculate average service feedback rating for a waiter from all their feedbacks.

        Returns None when the waiter has no feedback yet.
        """
        feedbacks = self._feedback_service_repo.find_all_by_waiter_id(waiter_id)
        if not feedbacks:
            return None
        return sum(fb.rate for fb in feedbacks) / len(feedbacks)

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
        now = datetime.now(UTC)
        feedback_date = self._feedback_date_for(reservation)
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
                    date=feedback_date,
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

        self._publish_feedback_event(
            FeedbackEventMessage(
                event_type=FeedbackEventType.CREATED,
                feedback_id=str(feedback_id),
                reservation_id=str(reservation.id) if reservation.id else None,
                customer_id=str(customer_id),
                feedback=request.comment or "",
                rate=request.rating,
                date=feedback_date.isoformat().replace("+00:00", "Z"),
                user_name=user_name,
                user_image_url=user_image_url,
                feedback_type=FeedbackType.SERVICE.value,
                location_id=None,
                location_address=None,
                waiter_id=str(waiter_id),
                timestamp=now.isoformat().replace("+00:00", "Z"),
            ),
            context="_create_service_feedback",
        )

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
        now = datetime.now(UTC)
        feedback_date = self._feedback_date_for(reservation)
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
                    date=feedback_date,
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

        if self._sqs is not None:
            location = self._location_repo.get(location_id)
            self._publish_feedback_event(
                FeedbackEventMessage(
                    event_type=FeedbackEventType.CREATED,
                    feedback_id=str(feedback_id),
                    reservation_id=str(reservation.id) if reservation.id else None,
                    customer_id=str(customer_id),
                    feedback=request.comment or "",
                    rate=request.rating,
                    date=feedback_date.isoformat().replace("+00:00", "Z"),
                    user_name=user_name,
                    user_image_url=user_image_url,
                    feedback_type=FeedbackType.CULINARY.value,
                    location_id=str(location_id),
                    location_address=location.address if location else None,
                    waiter_id=None,
                    timestamp=now.isoformat().replace("+00:00", "Z"),
                ),
                context="_create_culinary_feedback",
            )

    def _update_service_feedback(
        self,
        request: UpdateFeedbackRequest,
        customer_id: UUID,
    ) -> bool:
        """Update service feedback for a reservation."""
        feedback_id = uuid5(NAMESPACE_URL, f"service:{request.reservation_id}")
        current = self._feedback_service_repo.get(feedback_id)

        if current is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Service feedback for this reservation was not found.",
            )

        if current.customer_id != customer_id:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Customers can edit feedback only for their own reservations.",
            )

        next_rate = request.rating if request.rating is not None else current.rate
        next_comment = (
            request.comment if request.comment is not None else current.feedback
        )

        if (
            request.rating is not None
            and request.comment is not None
            and next_rate == current.rate
            and next_comment == current.feedback
        ):
            return False

        self._feedback_service_repo.update(
            ServiceFeedback(
                id=current.id,
                reservation_id=current.reservation_id,
                customer_id=current.customer_id,
                user_name=current.user_name,
                user_image_url=current.user_image_url,
                feedback=next_comment,
                rate=next_rate,
                date=current.date,
                waiter_id=current.waiter_id,
            )
        )

        now = datetime.now(UTC)
        self._publish_feedback_event(
            FeedbackEventMessage(
                event_type=FeedbackEventType.EDITED,
                feedback_id=str(current.id),
                reservation_id=(
                    str(current.reservation_id) if current.reservation_id else None
                ),
                customer_id=(str(current.customer_id) if current.customer_id else None),
                feedback=next_comment,
                rate=next_rate,
                date=current.date.isoformat().replace("+00:00", "Z"),
                user_name=current.user_name,
                user_image_url=current.user_image_url,
                feedback_type=FeedbackType.SERVICE.value,
                location_id=None,
                location_address=None,
                waiter_id=str(current.waiter_id),
                timestamp=now.isoformat().replace("+00:00", "Z"),
            ),
            context="_update_service_feedback",
        )
        return True

    def _update_culinary_feedback(
        self,
        request: UpdateFeedbackRequest,
        customer_id: UUID,
    ) -> bool:
        """Update culinary feedback for a reservation."""
        feedback_id = uuid5(NAMESPACE_URL, f"culinary:{request.reservation_id}")
        current = self._feedback_cuisine_repo.get(feedback_id)

        if current is None:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_RESOURCE_NOT_FOUND_CODE,
                "Culinary feedback for this reservation was not found.",
            )

        if current.customer_id != customer_id:
            raise ApplicationException(
                HttpStatusCode.RESPONSE_FORBIDDEN_CODE,
                "Customers can edit feedback only for their own reservations.",
            )

        next_rate = request.rating if request.rating is not None else current.rate
        next_comment = (
            request.comment if request.comment is not None else current.feedback
        )

        if (
            request.rating is not None
            and request.comment is not None
            and next_rate == current.rate
            and next_comment == current.feedback
        ):
            return False

        self._feedback_cuisine_repo.update(
            FeedbackCuisine(
                id=current.id,
                reservation_id=current.reservation_id,
                customer_id=current.customer_id,
                user_name=current.user_name,
                user_image_url=current.user_image_url,
                feedback=next_comment,
                rate=next_rate,
                date=current.date,
                location_id=current.location_id,
            )
        )

        if self._sqs is not None:
            now = datetime.now(UTC)
            location = self._location_repo.get(current.location_id)
            self._publish_feedback_event(
                FeedbackEventMessage(
                    event_type=FeedbackEventType.EDITED,
                    feedback_id=str(current.id),
                    reservation_id=(
                        str(current.reservation_id) if current.reservation_id else None
                    ),
                    customer_id=(
                        str(current.customer_id) if current.customer_id else None
                    ),
                    feedback=next_comment,
                    rate=next_rate,
                    date=current.date.isoformat().replace("+00:00", "Z"),
                    user_name=current.user_name,
                    user_image_url=current.user_image_url,
                    feedback_type=FeedbackType.CULINARY.value,
                    location_id=str(current.location_id),
                    location_address=location.address if location else None,
                    waiter_id=None,
                    timestamp=now.isoformat().replace("+00:00", "Z"),
                ),
                context="_update_culinary_feedback",
            )
        return True

    def _publish_feedback_event(
        self,
        message: FeedbackEventMessage,
        *,
        context: str,
    ) -> None:
        """Best-effort publish a feedback lifecycle event to the SQS event queue.

        Publishing is best-effort and must never break the API response: the
        call is skipped when no ``SqsService`` is configured (local dev / unit
        tests) and any exception is caught and logged. ``context`` names the
        originating call site so the log line identifies which action failed.

        Args:
            message: The feedback event envelope to publish.
            context: Name of the calling method, used in the failure log line.

        """
        if self._sqs is None:
            return
        try:
            self._sqs.publish(self._settings.event_queue_url, message)
        except Exception:
            logger.error(f"SQS publish failed in {context}", exc_info=True)

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

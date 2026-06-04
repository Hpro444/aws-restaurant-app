"""Unit tests for FeedbackService feedback creation flow."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock
from uuid import NAMESPACE_URL, uuid4, uuid5

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    from commons.exceptions import ApplicationException
    from domain.reservation import Reservation
    from domain.slot import Slot
    from domain.table import Table
    from dto.feedbacks import LeaveFeedbackRequest
    from enums.feedback_type import FeedbackType
    from enums.reservation_status import ReservationStatus
    from services.feedback_service import FeedbackService


class TestFeedbackService(TestCase):
    """Tests for service-layer feedback creation use-cases."""

    def setUp(self) -> None:
        """Build service with mocked repositories."""
        self.feedback_cuisine_repo = MagicMock()
        self.feedback_service_repo = MagicMock()
        self.customer_repo = MagicMock()
        self.reservation_repo = MagicMock()
        self.slot_repo = MagicMock()
        self.table_repo = MagicMock()

        self.service = FeedbackService(
            feedback_cuisine_repo=self.feedback_cuisine_repo,
            feedback_service_repo=self.feedback_service_repo,
            customer_repo=self.customer_repo,
            reservation_repo=self.reservation_repo,
            slot_repo=self.slot_repo,
            table_repo=self.table_repo,
        )

        self.customer_id = uuid4()
        self.reservation_id = uuid4()
        self.waiter_id = uuid4()

        self.reservation = Reservation(
            id=self.reservation_id,
            customer_id=self.customer_id,
            waiter_id=self.waiter_id,
            created_at=datetime.now(UTC),
            slot_ids=[uuid4()],
            status=ReservationStatus.FINISHED,
            number_of_guests=2,
        )
        self.customer_repo.get.return_value = SimpleNamespace(
            fname="John",
            lname="Doe",
            image_url="https://example.com/avatar.png",
        )

    def test_leave_feedback_service_persists_service_feedback(self) -> None:
        """Service feedback should use waiter_id resolved from reservation."""
        self.reservation_repo.get.return_value = self.reservation
        request = LeaveFeedbackRequest(
            reservation_id=self.reservation_id,
            type=FeedbackType.SERVICE,
            rating=5,
            comment="Excellent service",
        )

        self.service.leave_feedback(request=request, customer_id=self.customer_id)

        self.feedback_service_repo.create.assert_called_once()
        created = self.feedback_service_repo.create.call_args.args[0]
        self.assertEqual(
            created.id,
            uuid5(NAMESPACE_URL, f"service:{self.reservation_id}"),
        )
        self.assertEqual(created.reservation_id, self.reservation_id)
        self.assertEqual(created.customer_id, self.customer_id)
        self.assertEqual(created.waiter_id, self.waiter_id)
        self.assertEqual(created.user_name, "John Doe")
        self.assertEqual(created.user_image_url, "https://example.com/avatar.png")
        self.assertEqual(created.feedback, "Excellent service")
        self.assertEqual(created.rate, 5)
        self.feedback_cuisine_repo.create.assert_not_called()

    def test_leave_feedback_culinary_persists_cuisine_feedback(self) -> None:
        """Culinary feedback should resolve location from reservation slots."""
        location_id = uuid4()
        table_id = uuid4()
        self.reservation_repo.get.return_value = self.reservation
        self.slot_repo.find_by_ids.return_value = [
            Slot(
                id=self.reservation.slot_ids[0],
                table_id=table_id,
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                date=datetime.now(UTC),
            )
        ]
        self.table_repo.get.return_value = Table(
            id=table_id,
            location_id=location_id,
            table_number=1,
            capacity=4,
        )
        request = LeaveFeedbackRequest(
            reservation_id=self.reservation_id,
            type=FeedbackType.CULINARY,
            rating=4,
            comment="Great food",
        )

        self.service.leave_feedback(request=request, customer_id=self.customer_id)

        self.feedback_cuisine_repo.create.assert_called_once()
        created = self.feedback_cuisine_repo.create.call_args.args[0]
        self.assertEqual(
            created.id,
            uuid5(NAMESPACE_URL, f"culinary:{self.reservation_id}"),
        )
        self.assertEqual(created.reservation_id, self.reservation_id)
        self.assertEqual(created.location_id, location_id)
        self.assertEqual(created.customer_id, self.customer_id)
        self.assertEqual(created.user_name, "John Doe")
        self.assertEqual(created.user_image_url, "https://example.com/avatar.png")
        self.assertEqual(created.feedback, "Great food")
        self.assertEqual(created.rate, 4)
        self.feedback_service_repo.create.assert_not_called()

    def test_leave_feedback_raises_404_when_reservation_missing(self) -> None:
        """Unknown reservation_id should raise a 404 application error."""
        self.reservation_repo.get.return_value = None
        request = LeaveFeedbackRequest(
            reservation_id=self.reservation_id,
            type=FeedbackType.SERVICE,
            rating=5,
        )

        with self.assertRaises(ApplicationException) as exc:
            self.service.leave_feedback(request=request, customer_id=self.customer_id)

        self.assertEqual(exc.exception.code, 404)
        self.feedback_service_repo.create.assert_not_called()
        self.feedback_cuisine_repo.create.assert_not_called()

    def test_leave_feedback_raises_403_for_foreign_reservation(self) -> None:
        """Customers cannot leave feedback for another customer's reservation."""
        self.reservation_repo.get.return_value = Reservation(
            id=self.reservation_id,
            customer_id=uuid4(),
            waiter_id=self.waiter_id,
            created_at=datetime.now(UTC),
            slot_ids=[uuid4()],
            status=ReservationStatus.RESERVED,
            number_of_guests=2,
        )
        request = LeaveFeedbackRequest(
            reservation_id=self.reservation_id,
            type=FeedbackType.SERVICE,
            rating=5,
            comment="Should fail",
        )

        with self.assertRaises(ApplicationException) as exc:
            self.service.leave_feedback(request=request, customer_id=self.customer_id)

        self.assertEqual(exc.exception.code, 403)
        self.feedback_service_repo.create.assert_not_called()
        self.feedback_cuisine_repo.create.assert_not_called()

    def test_service_feedback_rejected_when_reservation_not_started(self) -> None:
        """Service feedback requires IN_PROGRESS or FINISHED reservation status."""
        self.reservation_repo.get.return_value = Reservation(
            id=self.reservation_id,
            customer_id=self.customer_id,
            waiter_id=self.waiter_id,
            created_at=datetime.now(UTC),
            slot_ids=[uuid4()],
            status=ReservationStatus.RESERVED,
            number_of_guests=2,
        )
        request = LeaveFeedbackRequest(
            reservation_id=self.reservation_id,
            type=FeedbackType.SERVICE,
            rating=5,
            comment="Too early",
        )

        with self.assertRaises(ApplicationException) as exc:
            self.service.leave_feedback(request=request, customer_id=self.customer_id)

        self.assertEqual(exc.exception.code, 422)
        self.feedback_service_repo.create.assert_not_called()

    def test_service_feedback_allowed_for_in_progress(self) -> None:
        """Service feedback is valid while reservation is IN_PROGRESS."""
        self.reservation_repo.get.return_value = Reservation(
            id=self.reservation_id,
            customer_id=self.customer_id,
            waiter_id=self.waiter_id,
            created_at=datetime.now(UTC),
            slot_ids=[uuid4()],
            status=ReservationStatus.IN_PROGRESS,
            number_of_guests=2,
        )
        request = LeaveFeedbackRequest(
            reservation_id=self.reservation_id,
            type=FeedbackType.SERVICE,
            rating=5,
            comment="Good support",
        )

        self.service.leave_feedback(request=request, customer_id=self.customer_id)

        self.feedback_service_repo.create.assert_called_once()

    def test_culinary_feedback_rejected_when_not_finished(self) -> None:
        """Culinary feedback requires FINISHED reservation status."""
        self.reservation_repo.get.return_value = Reservation(
            id=self.reservation_id,
            customer_id=self.customer_id,
            waiter_id=self.waiter_id,
            created_at=datetime.now(UTC),
            slot_ids=[uuid4()],
            status=ReservationStatus.IN_PROGRESS,
            number_of_guests=2,
        )
        request = LeaveFeedbackRequest(
            reservation_id=self.reservation_id,
            type=FeedbackType.CULINARY,
            rating=4,
            comment="Too early culinary",
        )

        with self.assertRaises(ApplicationException) as exc:
            self.service.leave_feedback(request=request, customer_id=self.customer_id)

        self.assertEqual(exc.exception.code, 422)
        self.feedback_cuisine_repo.create.assert_not_called()

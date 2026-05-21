"""Tests for the GET /bookings/tables availability endpoint."""

from datetime import date, timedelta
from unittest.mock import MagicMock
from uuid import UUID

from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_get_event,
    status,
)

_PATH = "/bookings/tables"
_TOMORROW = (date.today() + timedelta(days=1)).isoformat()
_VALID_PARAMS = {
    "location_id": "f6d6b8df-a7d5-4f06-8dd0-739d2f4f8df3",
    "date": _TOMORROW,
    "guests_number": "2",
}
_MOCK_RESPONSE_DATA = {
    "tables": [
        {
            "table_id": "f6d6b8df-a7d5-4f06-8dd0-739d2f4f8df3",
            "table_number": 1,
            "capacity": 4,
            "location_name": "48 Rustaveli Avenue, Tbilisi",
            "available_slots": [
                {
                    "slot_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "start_time": f"{_TOMORROW}T10:00:00+00:00",
                    "end_time": f"{_TOMORROW}T11:30:00+00:00",
                }
            ],
        }
    ]
}


class TestAvailableTables(ApiHandlerLambdaTestCase):
    """Tests for the GET /bookings/tables availability flow."""

    def setUp(self) -> None:
        """Set up handler with a mocked table availability service."""
        super().setUp()
        mock_response = MagicMock()
        mock_response.model_dump.return_value = _MOCK_RESPONSE_DATA
        self.HANDLER._table_availability_service.get_available_tables = MagicMock(
            return_value=mock_response
        )

    def test_success_returns_200_with_tables(self) -> None:
        """A valid request with all required params should return 200 with a tables list."""
        result = self.HANDLER.lambda_handler(make_get_event(_PATH, _VALID_PARAMS), {})
        self.assertEqual(status(result), 200)
        self.assertIn("tables", body(result))
        self.assertEqual(
            body(result)["tables"][0]["location_name"],
            "48 Rustaveli Avenue, Tbilisi",
        )
        self.HANDLER._table_availability_service.get_available_tables.assert_called_once_with(
            location_id=UUID(_VALID_PARAMS["location_id"]),
            booking_date=_TOMORROW,
            guests_number=2,
            from_time=None,
        )

    def test_success_with_from_time_forwards_filter_to_service(self) -> None:
        """Optional from_time must be validated and forwarded to the service."""
        params = {**_VALID_PARAMS, "from_time": "12:00"}

        result = self.HANDLER.lambda_handler(make_get_event(_PATH, params), {})

        self.assertEqual(status(result), 200)
        self.HANDLER._table_availability_service.get_available_tables.assert_called_once_with(
            location_id=UUID(_VALID_PARAMS["location_id"]),
            booking_date=_TOMORROW,
            guests_number=2,
            from_time="12:00",
        )

    def test_invalid_guests_number_returns_422(self) -> None:
        """A non-integer guests_number query param should return 422 before the service is called."""
        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {**_VALID_PARAMS, "guests_number": "two"}), {}
        )
        self.assertEqual(status(result), 422)
        self.assertEqual(body(result)["errors"][0]["field"], "guests_number")
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

    def test_missing_location_id_returns_422(self) -> None:
        """A request without location_id should fail validation and return 422."""
        params = {k: v for k, v in _VALID_PARAMS.items() if k != "location_id"}
        result = self.HANDLER.lambda_handler(make_get_event(_PATH, params), {})
        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

    def test_missing_date_returns_422(self) -> None:
        """A request without date should fail validation and return 422."""
        params = {k: v for k, v in _VALID_PARAMS.items() if k != "date"}
        result = self.HANDLER.lambda_handler(make_get_event(_PATH, params), {})
        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

    def test_missing_guests_number_returns_422(self) -> None:
        """A request without guests_number should fail validation and return 422."""
        params = {k: v for k, v in _VALID_PARAMS.items() if k != "guests_number"}
        result = self.HANDLER.lambda_handler(make_get_event(_PATH, params), {})
        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

    def test_no_query_params_returns_422(self) -> None:
        """A request with no query params at all should fail validation and return 422."""
        result = self.HANDLER.lambda_handler(make_get_event(_PATH, None), {})
        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

    def test_invalid_date_format_returns_422(self) -> None:
        """A date in DD-MM-YYYY format should fail validation and return 422."""
        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {**_VALID_PARAMS, "date": "16-05-2026"}), {}
        )
        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

    def test_past_date_returns_422(self) -> None:
        """A date in the past should fail the bookability window check and return 422."""
        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {**_VALID_PARAMS, "date": "2020-01-01"}), {}
        )
        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

    def test_date_beyond_30_days_returns_422(self) -> None:
        """A date more than 30 days ahead should fail the bookability window check and return 422."""
        far_future = (date.today() + timedelta(days=31)).isoformat()
        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {**_VALID_PARAMS, "date": far_future}), {}
        )
        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

    def test_guests_number_zero_returns_422(self) -> None:
        """guests_number of 0 should fail the gt=0 validation and return 422."""
        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {**_VALID_PARAMS, "guests_number": "0"}), {}
        )
        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

    def test_guests_number_above_max_returns_422(self) -> None:
        """guests_number above 10 should fail the le=10 validation and return 422."""
        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {**_VALID_PARAMS, "guests_number": "11"}), {}
        )
        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

    def test_invalid_location_uuid_returns_422(self) -> None:
        """A malformed location_id UUID should fail validation and return 422."""
        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {**_VALID_PARAMS, "location_id": "not-a-uuid"}), {}
        )
        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

    def test_invalid_from_time_format_returns_422(self) -> None:
        """from_time must be in HH:MM format."""
        result = self.HANDLER.lambda_handler(
            make_get_event(_PATH, {**_VALID_PARAMS, "from_time": "9am"}), {}
        )
        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

    def test_invalid_from_time_format_bad_value_returns_422(self) -> None:
        """from_time with invalid format should fail validation and return 422."""
        result = self.HANDLER.lambda_handler(
            make_get_event(
                _PATH,
                {**_VALID_PARAMS, "from_time": "25:00"},
            ),
            {},
        )
        self.assertEqual(status(result), 422)
        self.HANDLER._table_availability_service.get_available_tables.assert_not_called()

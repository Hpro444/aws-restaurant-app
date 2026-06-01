"""Tests that handle_request dispatches correctly by path and HTTP method."""

from pyapp.tests.test_api_handler import (
    ApiHandlerLambdaTestCase,
    body,
    make_event,
    status,
)

_SIGN_UP_PATH = "/auth/sign-up"
_SIGN_IN_PATH = "/auth/sign-in"
_REFRESH_PATH = "/auth/refresh"
_LOGOUT_PATH = "/auth/logout"
_BOOKINGS_TABLES_PATH = "/bookings/tables"
_DISHES_POPULAR_PATH = "/dishes/popular"
_UNKNOWN_PATH = "/unknown"
_MALFORMED_LOCATION_SPECIALITY_PATH = "/api/locations//speciality-dishes"
_LOCATION_SPECIALITY_PATH = (
    "/locations/f6d6b8df-a7d5-4f06-8dd0-739d2f4f8df3/speciality-dishes"
)
_BOOKINGS_CLIENT_PATH = "/bookings/client"
_BOOKINGS_CLIENT_DETAILS_PATH = "/bookings/client/43f656ab-2e53-4893-9a79-6378a5f5f57f"
_BOOKINGS_CLIENT_CANCEL_PATH = (
    "/bookings/client/43f656ab-2e53-4893-9a79-6378a5f5f57f/cancel"
)

_DUMMY_BODY = {
    "firstName": "Jane",
    "lastName": "Doe",
    "email": "jane@example.com",
    "password": "Secure123!",
}


class TestRouting(ApiHandlerLambdaTestCase):
    """Tests that handle_request dispatches correctly by path and method."""

    def test_unknown_path_returns_404(self) -> None:
        """An unrecognised path should return 404."""
        result = self.HANDLER.lambda_handler(make_event(_UNKNOWN_PATH, "POST", {}), {})

        self.assertEqual(status(result), 404)
        self.assertEqual(body(result)["message"], "Route not found")

    def test_malformed_double_slash_path_returns_404_with_json_message(self) -> None:
        """A malformed path with duplicate slashes should return 404 JSON payload."""
        result = self.HANDLER.lambda_handler(
            make_event(_MALFORMED_LOCATION_SPECIALITY_PATH, "GET", {}),
            {},
        )

        self.assertEqual(status(result), 404)
        self.assertEqual(body(result)["message"], "Route not found")

    def test_blank_location_id_in_path_parameters_returns_422_required(self) -> None:
        """A routed request with blank pathParameters.id should return required-field 422."""
        result = self.HANDLER.lambda_handler(
            {
                "path": _LOCATION_SPECIALITY_PATH,
                "httpMethod": "GET",
                "pathParameters": {"id": "   "},
                "queryStringParameters": None,
            },
            {},
        )

        self.assertEqual(status(result), 422)
        self.assertEqual(body(result)["errors"][0]["field"], "id")
        self.assertEqual(body(result)["errors"][0]["message"], "'id' is required")

    def test_wrong_method_on_sign_up_returns_404(self) -> None:
        """A GET to the sign-up path should return 404."""
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(
                    make_event(_SIGN_UP_PATH, "GET", _DUMMY_BODY), {}
                )
            ),
            404,
        )

    def test_wrong_method_on_sign_in_returns_404(self) -> None:
        """A GET to the sign-in path should return 404."""
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(
                    make_event(_SIGN_IN_PATH, "GET", _DUMMY_BODY), {}
                )
            ),
            404,
        )

    def test_wrong_method_on_refresh_returns_404(self) -> None:
        """A GET to the refresh path should return 404."""
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(make_event(_REFRESH_PATH, "GET", {}), {})
            ),
            404,
        )

    def test_wrong_method_on_bookings_tables_returns_404(self) -> None:
        """A POST to the bookings/tables path should return 404."""
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(
                    make_event(_BOOKINGS_TABLES_PATH, "POST", {}), {}
                )
            ),
            404,
        )

    def test_wrong_method_on_logout_returns_404(self) -> None:
        """A GET to the logout path should return 404."""
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(make_event(_LOGOUT_PATH, "GET", {}), {})
            ),
            404,
        )

    def test_wrong_method_on_dishes_popular_returns_404(self) -> None:
        """A POST to the popular dishes path should return 404."""
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(
                    make_event(_DISHES_POPULAR_PATH, "POST", {}), {}
                )
            ),
            404,
        )

    def test_wrong_method_on_location_speciality_returns_404(self) -> None:
        """A POST to the location speciality path should return 404."""
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(
                    make_event(_LOCATION_SPECIALITY_PATH, "POST", {}), {}
                )
            ),
            404,
        )

    def test_wrong_method_on_bookings_client_returns_404(self) -> None:
        """A DELETE to the bookings/client path should return 404."""
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(
                    make_event(_BOOKINGS_CLIENT_PATH, "DELETE", {}), {}
                )
            ),
            404,
        )

    def test_wrong_method_on_bookings_client_details_returns_404(self) -> None:
        """A POST to the bookings/client/{id} path should return 404."""
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(
                    make_event(_BOOKINGS_CLIENT_DETAILS_PATH, "POST", {}), {}
                )
            ),
            404,
        )

    def test_wrong_method_on_bookings_client_cancel_returns_404(self) -> None:
        """A GET to the bookings/client/{id}/cancel path should return 404."""
        self.assertEqual(
            status(
                self.HANDLER.lambda_handler(
                    make_event(_BOOKINGS_CLIENT_CANCEL_PATH, "GET", {}), {}
                )
            ),
            404,
        )

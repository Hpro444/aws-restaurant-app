"""Tests that handle_request dispatches correctly by path and HTTP method."""

from pyapp.tests.test_api_handler import ApiHandlerLambdaTestCase, make_event, status

_SIGN_UP_PATH = "/auth/sign-up"
_SIGN_IN_PATH = "/auth/sign-in"
_REFRESH_PATH = "/auth/refresh"
_LOGOUT_PATH = "/auth/logout"
_BOOKINGS_TABLES_PATH = "/bookings/tables"

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
        self.assertEqual(
            status(self.HANDLER.lambda_handler(make_event("/unknown", "POST", {}), {})),
            404,
        )

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

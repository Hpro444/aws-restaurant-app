"""Base test case setup for the api-handler Lambda."""

import importlib
import unittest

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    LAMBDA_HANDLER = importlib.import_module("lambdas.api-handler.handler")


class ApiHandlerLambdaTestCase(unittest.TestCase):
    """Common setup for api-handler Lambda test cases."""

    def setUp(self) -> None:
        """Instantiate a fresh ApiHandler before each test."""
        self.HANDLER = LAMBDA_HANDLER.ApiHandler()

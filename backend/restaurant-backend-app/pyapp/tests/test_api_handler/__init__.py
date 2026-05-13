"""Base test case setup for the api-handler Lambda."""

import importlib
import json
import unittest

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    LAMBDA_HANDLER = importlib.import_module("lambdas.api-handler.handler")


class ApiHandlerLambdaTestCase(unittest.TestCase):
    """Common setup for api-handler Lambda test cases."""

    def setUp(self) -> None:
        """Instantiate a fresh ApiHandler before each test."""
        self.HANDLER = LAMBDA_HANDLER.ApiHandler()


def make_event(path: str, method: str, body: dict) -> dict:
    """Build a minimal API Gateway-style Lambda event."""
    return {"path": path, "httpMethod": method, "body": json.dumps(body)}


def status(result: dict) -> int:
    """Extract the HTTP status code from a Lambda proxy response."""
    return result["statusCode"]


def body(result: dict) -> dict:
    """Parse and return the response body dict from a Lambda proxy response."""
    return json.loads(result["body"])

"""Test package for the report sender lambda."""

import importlib
import unittest

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    LAMBDA_HANDLER = importlib.import_module("lambdas.report_sender_lambda.handler")


class ReportSenderLambdaTestCase(unittest.TestCase):
    """Common setup for report sender lambda tests."""

    def setUp(self) -> None:
        """Instantiate lambda handler before each test."""
        self.HANDLER = LAMBDA_HANDLER.ReportSenderLambda()

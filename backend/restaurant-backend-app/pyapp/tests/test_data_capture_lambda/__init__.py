"""Test package for the data capture lambda."""

import importlib
import unittest

from pyapp.tests import ImportFromSourceContext

with ImportFromSourceContext():
    LAMBDA_HANDLER = importlib.import_module("lambdas.data_capture_lambda.handler")


class DataCaptureLambdaLambdaTestCase(unittest.TestCase):
    """Common setups for data capture lambda tests."""

    def setUp(self) -> None:
        """Instantiate the lambda handler before each test."""
        self.HANDLER = LAMBDA_HANDLER.DataCaptureLambda()

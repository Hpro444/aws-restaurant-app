"""Enum for feedback categories accepted by the API."""

from enum import Enum


class FeedbackType(str, Enum):
    """Supported feedback categories for customer submissions."""

    SERVICE = "service"
    CULINARY = "culinary"

"""Enum definitions for dish availability states."""

from enum import Enum


class DishState(str, Enum):
    """Availability states assignable to a dish."""

    AVAILABLE = "Available"
    ON_STOP = "On Stop"

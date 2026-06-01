"""Enum definitions for dish type categories."""

from enum import Enum


class DishType(str, Enum):
    """Category types assignable to a dish."""

    APPETIZER = "APPETIZER"
    DESSERT = "DESSERT"
    MAIN_COURSE = "MAIN_COURSE"

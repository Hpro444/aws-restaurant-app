"""Enum definitions for dish type categories."""

from enum import Enum


class DishType(str, Enum):
    """Category types assignable to a dish."""

    APPETIZER = "Appetizer"
    DESSERT = "Dessert"
    MAIN_COURSE = "Main Course"
    DRINK = "Drink"

"""Enum definitions for user roles in the restaurant application."""

from enum import Enum


class UserRole(str, Enum):
    """Roles assignable to a restaurant application user."""

    ADMIN = "Admin"
    USER = "User"
    WAITER = "Waiter"

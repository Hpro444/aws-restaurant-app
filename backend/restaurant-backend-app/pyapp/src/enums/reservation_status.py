"""Enum definitions for reservation statuses in the restaurant application."""

from enum import Enum


class ReservationStatus(str, Enum):
    """Statuses assignable to a reservation."""

    RESERVED = "RESERVED"
    IN_PROGRESS = "IN_PROGRESS"
    CANCELLED = "CANCELLED"
    FINISHED = "FINISHED"
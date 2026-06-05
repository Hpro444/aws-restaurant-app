"""Enum definitions for reservation statuses in the restaurant application."""

from enum import Enum


class ReservationStatus(str, Enum):
    """Statuses assignable to a reservation."""

    RESERVED = "Reserved"
    IN_PROGRESS = "In Progress"
    CANCELLED = "Cancelled"
    FINISHED = "Finished"

"""Enum definitions for slot statuses in the restaurant application."""

from enum import Enum


class SlotStatus(str, Enum):
    """Statuses assignable to a table time slot."""

    FREE = "FREE"
    RESERVED = "RESERVED"

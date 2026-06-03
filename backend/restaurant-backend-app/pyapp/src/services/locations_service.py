"""Service for listing restaurant locations."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from uuid import UUID

from dto.locations import LocationAddressResponse, LocationResponse
from repositories.feedback_cuisine_repository import FeedbackCuisineRepository
from repositories.location_repository import LocationRepository
from repositories.table_repository import TableRepository


class LocationsService:
    """Handles retrieval and response mapping for location listings."""

    def __init__(
        self,
        location_repository: LocationRepository | None = None,
        table_repository: TableRepository | None = None,
        feedback_cuisine_repository: FeedbackCuisineRepository | None = None,
    ) -> None:
        """Initialize dependencies, creating them if not provided."""
        self._location_repository = location_repository or LocationRepository()
        self._table_repository = table_repository or TableRepository()
        self._feedback_cuisine_repository = (
            feedback_cuisine_repository or FeedbackCuisineRepository()
        )

    def get_locations(self) -> list[LocationResponse]:
        """Return all locations mapped to the public locations response contract."""
        locations = self._location_repository.scan()

        return [
            LocationResponse(
                id=str(location.id),
                address=location.address,
                description=location.description,
                # TODO: ukoliko se predje na RDS, ovo bi trebalo da se izracunava direktno u upitu
                total_capacity=self._calculate_total_capacity(location.id),
                # TODO: trenutno simulirano zbog demo-a, ovo bi trebalo da se izracunava direktno u upitu
                average_occupancy=self._simulate_average_occupancy(location.id),
                image_url=location.image_url,
                # TODO: ukoliko se predje na RDS, ovo bi trebalo da se izracunava direktno u upitu
                rating=self._calculate_rating(location.id),
            )
            for location in locations
        ]

    def get_location_addresses(self) -> list[LocationAddressResponse]:
        """Return all location ids and addresses for compact picker/filter responses."""
        locations = self._location_repository.scan()
        return [
            LocationAddressResponse(
                location_id=str(location.id),
                location_address=location.address,
            )
            for location in locations
        ]

    def get_location_by_id(self, location_id: UUID) -> LocationResponse | None:
        """Return a single location by ID, or None if not found."""
        location = self._location_repository.get(location_id)
        if not location:
            return None

        return LocationResponse(
            id=str(location.id),
            address=location.address,
            description=location.description,
            total_capacity=self._calculate_total_capacity(location.id),
            average_occupancy=self._simulate_average_occupancy(location.id),
            image_url=location.image_url,
            rating=self._calculate_rating(location.id),
        )

    def get_valid_slot_times(
        self,
        location_id: UUID,
    ) -> dict[str, list[str]] | None:
        """Return valid slot start/end times for a location, or None if missing."""
        slot_times = self._get_valid_slot_times(location_id)
        if slot_times is None:
            return None

        start_times, end_times = slot_times
        return {
            "start_times": start_times,
            "end_times": end_times,
        }

    def _get_valid_slot_times(
        self, location_id: UUID
    ) -> tuple[list[str], list[str]] | None:
        """Return calculated slot start/end times for location, or None if missing."""
        location = self._location_repository.get(location_id)
        if not location:
            return None

        return self._calculate_slot_times(location.open_time, location.close_time)

    def _calculate_rating(self, location_id) -> float:
        """Calculate the average rating for a location from cuisine feedback only. Returns 1 decimal place, or 0.0 if no ratings."""
        feedbacks = list(
            self._feedback_cuisine_repository.find_by_location_id(location_id)
        )
        ratings = [
            f.rate for f in feedbacks if hasattr(f, "rate") and f.rate is not None
        ]
        if not ratings:
            return 0.0
        avg = sum(ratings) / len(ratings)
        return round(avg, 1)

    def _calculate_total_capacity(self, location_id) -> int:
        """Return total seating capacity for a location as sum of table capacities."""
        tables = self._table_repository.find_by_location_id(location_id)
        return sum(table.capacity for table in tables)

    @staticmethod
    def _simulate_average_occupancy(location_id: UUID) -> int:
        """Return a stable placeholder occupancy between 25 and 100 inclusive."""
        return 25 + (location_id.int % 76)

    @staticmethod
    def _calculate_slot_times(
        open_time: time, close_time: time
    ) -> tuple[list[str], list[str]]:
        """Calculate slot starts/ends with fixed 90m duration and 15m gap."""
        reservation_duration = timedelta(minutes=90)
        slot_step = timedelta(minutes=105)

        base_day = datetime.min.date()
        current_start = datetime.combine(base_day, open_time)
        close_dt = datetime.combine(base_day, close_time)

        starts: list[str] = []
        ends: list[str] = []

        while current_start + reservation_duration <= close_dt:
            current_end = current_start + reservation_duration
            starts.append(current_start.strftime("%H:%M"))
            ends.append(current_end.strftime("%H:%M"))
            current_start += slot_step

        return starts, ends

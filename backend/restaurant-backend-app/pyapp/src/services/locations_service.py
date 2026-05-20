"""Service for listing restaurant locations."""

from __future__ import annotations

from uuid import UUID

from dto.locations import LocationResponse
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
                total_capacity=str(self._calculate_total_capacity(location.id)),
                # TODO: trenutno simulirano zbog demo-a, ovo bi trebalo da se izracunava direktno u upitu
                average_occupancy=self._simulate_average_occupancy(location.id),
                image_url=location.image_url,
                # TODO: ukoliko se predje na RDS, ovo bi trebalo da se izracunava direktno u upitu
                rating=self._calculate_rating(location.id),
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
            total_capacity=str(self._calculate_total_capacity(location.id)),
            average_occupancy=self._simulate_average_occupancy(location.id),
            image_url=location.image_url,
            rating=self._calculate_rating(location.id),
        )

    def _calculate_rating(self, location_id) -> str:
        """Calculate the average rating for a location from cuisine feedback only. Returns as a string with 1 decimal place, or '0' if no ratings."""
        feedbacks = list(
            self._feedback_cuisine_repository.find_by_location_id(location_id)
        )
        ratings = [
            f.rate for f in feedbacks if hasattr(f, "rate") and f.rate is not None
        ]
        if not ratings:
            return "0"
        avg = sum(ratings) / len(ratings)
        return f"{avg:.1f}"

    def _calculate_total_capacity(self, location_id) -> int:
        """Return total seating capacity for a location as sum of table capacities."""
        tables = self._table_repository.find_by_location_id(location_id)
        return sum(table.capacity for table in tables)

    @staticmethod
    def _simulate_average_occupancy(location_id: UUID) -> str:
        """Return a stable placeholder occupancy between 25 and 100 inclusive."""
        return str(25 + (location_id.int % 76))

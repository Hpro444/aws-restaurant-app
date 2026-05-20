"""DTOs for the GET /locations endpoint."""

from pydantic import BaseModel


class LocationResponse(BaseModel):
    """One location card returned by GET /locations."""

    id: str
    address: str
    description: str
    total_capacity: str
    average_occupancy: str
    image_url: str
    rating: str
